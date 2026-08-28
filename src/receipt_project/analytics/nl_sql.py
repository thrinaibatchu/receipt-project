import os
from typing import Any

import psycopg
import sqlglot
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel


MODEL_NAME = "gemini-3.5-flash-lite"

RETRYABLE_HTTP_STATUS_CODES = [
    408,
    429,
    500,
    502,
    503,
    504,
]

ALLOWED_TABLES = {
    "receipts",
    "receipt_items",
    "receipt_discounts",
    "products",
}

FORBIDDEN_NODE_NAMES = {
    "Insert",
    "Update",
    "Delete",
    "Create",
    "Drop",
    "Alter",
    "TruncateTable",
    "Command",
    "Merge",
    "Copy",
}


class SqlPlan(BaseModel):
    sql: str
    explanation: str


def get_database_url() -> str:
    load_dotenv()

    database_url = os.getenv("ANALYTICS_DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    return database_url


def get_gemini_api_key() -> str:
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing")

    return api_key


def create_gemini_client() -> genai.Client:
    return genai.Client(
        api_key=get_gemini_api_key(),
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=5,
                initial_delay=2.0,
                max_delay=16.0,
                exp_base=2,
                jitter=1.0,
                http_status_codes=RETRYABLE_HTTP_STATUS_CODES,
            ),
        ),
    )


def generate_sql_plan(question: str) -> SqlPlan:
    client = create_gemini_client()

    prompt = f"""
Translate the user's receipt-data question into PostgreSQL.

User question:
{question}

Available schema:

receipts
- id
- store_name
- purchase_date
- subtotal
- tax
- total
- transaction_id
- source_file
- source_hash
- receipt_fingerprint
- created_at

receipt_items
- id
- receipt_id
- product_id
- store_item_code
- raw_description
- quantity
- unit_price
- total_price

receipt_discounts
- id
- receipt_id
- raw_description
- amount
- related_item_code

products
- id
- canonical_name
- category

Relationships:
receipt_items.receipt_id = receipts.id
receipt_discounts.receipt_id = receipts.id
receipt_items.product_id = products.id

Rules:
1. Return exactly one read-only PostgreSQL query.
2. Only SELECT or WITH queries are allowed.
3. Never modify data or database structure.
4. Only use the four tables listed above.
5. Do not query system catalogs.
6. Do not use source_hash or receipt_fingerprint unless explicitly needed.
7. For item-name questions, use receipt_items.raw_description as the primary field.
8. Do not join products unless the user's question explicitly requires
   products.canonical_name or products.category.
9. product_id may be NULL for many receipt_items, so an INNER JOIN to products
   can incorrectly remove valid receipt items.
10. "How many times did I buy X?" means count distinct receipts containing X,
    using receipt_items.raw_description ILIKE.
11. "How many units of X did I buy?" or "How many X did I buy?" means
    SUM(receipt_items.quantity), filtering receipt_items.raw_description with ILIKE.
12. Monetary item spend uses receipt_items.total_price unless the question is
    specifically about receipt totals.
13. Use purchase_date for date filtering.
14. Do not invent columns.
15. Add LIMIT 100 for row-level result queries when appropriate.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SqlPlan,
        ),
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty SQL plan."
        )

    return SqlPlan.model_validate_json(
        response.text
    )


def validate_sql(sql: str) -> str:
    statements = sqlglot.parse(
        sql,
        read="postgres",
    )

    if len(statements) != 1:
        raise ValueError(
            "Exactly one SQL statement is required."
        )

    expression = statements[0]

    root_name = expression.__class__.__name__

    if root_name not in {
        "Select",
        "Union",
        "With",
    }:
        raise ValueError(
            "Only SELECT or WITH queries are allowed."
        )

    for node in expression.walk():
        if (
            node.__class__.__name__
            in FORBIDDEN_NODE_NAMES
        ):
            raise ValueError(
                "SQL contains a forbidden operation: "
                f"{node.__class__.__name__}"
            )

    table_names = {
        table.name
        for table in expression.find_all(
            sqlglot.exp.Table
        )
    }

    forbidden_tables = (
        table_names - ALLOWED_TABLES
    )

    if forbidden_tables:
        raise ValueError(
            "SQL references non-allowlisted tables: "
            + ", ".join(
                sorted(forbidden_tables)
            )
        )

    if not table_names:
        raise ValueError(
            "SQL must query at least one "
            "allowlisted table."
        )

    return expression.sql(
        dialect="postgres"
    )


def execute_read_only_sql(
    sql: str,
) -> tuple[
    list[str],
    list[tuple[Any, ...]],
]:
    validated_sql = validate_sql(sql)

    with psycopg.connect(
        get_database_url()
    ) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET TRANSACTION READ ONLY"
                )

                cursor.execute(
                    "SET LOCAL "
                    "statement_timeout = '5s'"
                )

                cursor.execute(
                    validated_sql
                )

                if cursor.description is None:
                    raise RuntimeError(
                        "Query returned no "
                        "result columns."
                    )

                columns = [
                    column.name
                    for column
                    in cursor.description
                ]

                rows = cursor.fetchmany(101)

                if len(rows) > 100:
                    raise RuntimeError(
                        "Query returned more "
                        "than 100 rows."
                    )

    return columns, rows


def ask_receipt_database(
    question: str,
) -> tuple[
    SqlPlan,
    list[str],
    list[tuple[Any, ...]],
]:
    plan = generate_sql_plan(
        question
    )

    columns, rows = (
        execute_read_only_sql(
            plan.sql
        )
    )

    return plan, columns, rows
