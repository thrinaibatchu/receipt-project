from __future__ import annotations

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

    database_url = os.getenv(
        "ANALYTICS_DATABASE_URL"
    )

    if not database_url:
        raise RuntimeError(
            "ANALYTICS_DATABASE_URL is missing"
        )

    return database_url


def get_gemini_api_key() -> str:
    load_dotenv()

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing"
        )

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
                http_status_codes=(
                    RETRYABLE_HTTP_STATUS_CODES
                ),
            ),
        ),
    )


def generate_sql_plan(
    question: str,
) -> SqlPlan:
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
- source_type
- warehouse_number
- register_number
- historical_transaction_number
- transaction_time
- historical_key
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
- source_row_number
- historical_row_type

receipt_discounts
- id
- receipt_id
- raw_description
- amount
- related_item_code
- source_row_number
- historical_row_type

products
- id
- canonical_name
- category

Relationships:
receipt_items.receipt_id = receipts.id
receipt_discounts.receipt_id = receipts.id
receipt_items.product_id = products.id

Transaction semantics:
- The receipts table represents transactions.
- A purchase transaction has receipts.total > 0.
- A return/refund transaction has receipts.total < 0.
- A zero-value transaction has receipts.total = 0.
- "transaction" means any row in receipts.
- Plain "receipt" means a purchase receipt, so use receipts.total > 0.
- "purchase" or "purchase receipt" means receipts.total > 0.
- "return" or "refund" means receipts.total < 0.
- "net spend" means SUM(receipts.total), including negative refunds.
- "total spend" without another qualifier also means net spend.

Rules:
1. Return exactly one read-only PostgreSQL query.
2. Only SELECT or WITH queries are allowed.
3. Never modify data or database structure.
4. Only use the four tables listed above.
5. Do not query system catalogs.
6. Do not use source_hash, receipt_fingerprint, or historical_key unless
   explicitly needed.
7. For item-name questions, use receipt_items.raw_description as the
   primary matching field.
8. Use ILIKE for natural-language item matching.
9. Do not join products unless the user's question explicitly requires
   products.canonical_name or products.category.
10. product_id may be NULL for many receipt_items, so an INNER JOIN to
    products can incorrectly remove valid receipt items.
11. "How many transactions do I have?" means COUNT(*) from receipts,
    with no purchase/refund filter unless another condition is stated.
12. "How many receipts do I have?" means count purchase receipts only,
    requiring receipts.total > 0.
13. "How many purchases do I have?" means receipts.total > 0.
14. "How many returns/refunds do I have?" means receipts.total < 0.
15. "How many times did I buy X?" means count distinct purchase
    transactions containing X. Join receipts to receipt_items and require:
    - receipts.total > 0
    - receipt_items.quantity > 0
    - receipt_items.raw_description ILIKE the item search term
16. "How many units of X did I buy?" or "How many X did I buy?" means
    gross purchased quantity. Join receipts to receipt_items and require:
    - receipts.total > 0
    - receipt_items.quantity > 0
    Then SUM(receipt_items.quantity).
17. If the user explicitly asks for net quantity, sum signed
    receipt_items.quantity across purchases and returns.
18. Questions asking when or where an item was bought should normally
    use purchase transactions only unless returns are explicitly requested.
19. Monetary item spend uses receipt_items.total_price unless the
    question is specifically about transaction totals.
20. For gross item purchase spend, use positive purchase transactions.
21. For net item spend, signed item totals may include returns.
22. Use purchase_date for date filtering.
23. Relative dates such as "last 90 days" should use CURRENT_DATE and
    PostgreSQL interval expressions.
24. Do not invent columns.
25. Add LIMIT 100 for row-level result queries when appropriate.
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

    root_name = (
        expression.__class__.__name__
    )

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
    validated_sql = validate_sql(
        sql
    )

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

                rows = cursor.fetchmany(
                    101
                )

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