import os
from datetime import date
from decimal import Decimal

import psycopg
from dotenv import load_dotenv


STORE_NAME_NORMALIZATIONS = {
    "COSTCO WHOLESALE": "Costco Wholesale",
    "COSTCO": "Costco Wholesale",
}


def normalize_store_name(store_name: str) -> str:
    normalized_key = store_name.strip().upper()

    return STORE_NAME_NORMALIZATIONS.get(
        normalized_key,
        store_name.strip(),
    )


def get_database_url() -> str:
    load_dotenv()

    database_url = os.getenv("ANALYTICS_DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    return database_url


def get_date_bounds() -> tuple[date | None, date | None]:
    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    MIN(purchase_date),
                    MAX(purchase_date)
                FROM receipts
                WHERE purchase_date IS NOT NULL
                """
            )

            return cursor.fetchone()


def get_receipt_count(
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM receipts
                WHERE (
                    %s::date IS NULL
                    OR purchase_date >= %s::date
                )
                  AND (
                    %s::date IS NULL
                    OR purchase_date <= %s::date
                )
                """,
                (
                    start_date,
                    start_date,
                    end_date,
                    end_date,
                ),
            )

            return cursor.fetchone()[0]


def get_total_spend(
    start_date: date | None = None,
    end_date: date | None = None,
) -> Decimal:
    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(total), 0)
                FROM receipts
                WHERE (
                    %s::date IS NULL
                    OR purchase_date >= %s::date
                )
                  AND (
                    %s::date IS NULL
                    OR purchase_date <= %s::date
                )
                """,
                (
                    start_date,
                    start_date,
                    end_date,
                    end_date,
                ),
            )

            return cursor.fetchone()[0]


def get_recent_receipts(
    limit: int = 10,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    store_name,
                    purchase_date,
                    total
                FROM receipts
                WHERE (
                    %s::date IS NULL
                    OR purchase_date >= %s::date
                )
                  AND (
                    %s::date IS NULL
                    OR purchase_date <= %s::date
                )
                ORDER BY
                    purchase_date DESC NULLS LAST,
                    id DESC
                LIMIT %s
                """,
                (
                    start_date,
                    start_date,
                    end_date,
                    end_date,
                    limit,
                ),
            )

            rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "store_name": normalize_store_name(row[1]),
            "raw_store_name": row[1],
            "purchase_date": row[2],
            "total": row[3],
        }
        for row in rows
    ]


def get_spend_by_store(
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    store_name,
                    total
                FROM receipts
                WHERE (
                    %s::date IS NULL
                    OR purchase_date >= %s::date
                )
                  AND (
                    %s::date IS NULL
                    OR purchase_date <= %s::date
                )
                """,
                (
                    start_date,
                    start_date,
                    end_date,
                    end_date,
                ),
            )

            rows = cursor.fetchall()

    grouped: dict[str, dict] = {}

    for store_name, total in rows:
        normalized_name = normalize_store_name(store_name)

        if normalized_name not in grouped:
            grouped[normalized_name] = {
                "store_name": normalized_name,
                "receipt_count": 0,
                "total_spend": Decimal("0"),
            }

        grouped[normalized_name]["receipt_count"] += 1
        grouped[normalized_name]["total_spend"] += total

    return sorted(
        grouped.values(),
        key=lambda row: (
            -row["total_spend"],
            row["store_name"],
        ),
    )


def get_spend_over_time(
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    purchase_date,
                    SUM(total) AS total_spend
                FROM receipts
                WHERE purchase_date IS NOT NULL
                  AND (
                    %s::date IS NULL
                    OR purchase_date >= %s::date
                  )
                  AND (
                    %s::date IS NULL
                    OR purchase_date <= %s::date
                  )
                GROUP BY purchase_date
                ORDER BY purchase_date
                """,
                (
                    start_date,
                    start_date,
                    end_date,
                    end_date,
                ),
            )

            rows = cursor.fetchall()

    return [
        {
            "purchase_date": row[0],
            "total_spend": row[1],
        }
        for row in rows
    ]


def get_top_items_by_quantity(
    limit: int = 10,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ri.raw_description,
                    SUM(ri.quantity) AS total_quantity
                FROM receipt_items ri
                JOIN receipts r
                    ON r.id = ri.receipt_id
                WHERE (
                    %s::date IS NULL
                    OR r.purchase_date >= %s::date
                )
                  AND (
                    %s::date IS NULL
                    OR r.purchase_date <= %s::date
                )
                GROUP BY ri.raw_description
                ORDER BY
                    total_quantity DESC,
                    ri.raw_description
                LIMIT %s
                """,
                (
                    start_date,
                    start_date,
                    end_date,
                    end_date,
                    limit,
                ),
            )

            rows = cursor.fetchall()

    return [
        {
            "raw_description": row[0],
            "total_quantity": row[1],
        }
        for row in rows
    ]


def get_top_items_by_spend(
    limit: int = 10,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ri.raw_description,
                    SUM(ri.total_price) AS total_spend
                FROM receipt_items ri
                JOIN receipts r
                    ON r.id = ri.receipt_id
                WHERE (
                    %s::date IS NULL
                    OR r.purchase_date >= %s::date
                )
                  AND (
                    %s::date IS NULL
                    OR r.purchase_date <= %s::date
                )
                GROUP BY ri.raw_description
                ORDER BY
                    total_spend DESC,
                    ri.raw_description
                LIMIT %s
                """,
                (
                    start_date,
                    start_date,
                    end_date,
                    end_date,
                    limit,
                ),
            )

            rows = cursor.fetchall()

    return [
        {
            "raw_description": row[0],
            "total_spend": row[1],
        }
        for row in rows
    ]


def search_items(
    search_text: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50,
) -> list[dict]:
    search_pattern = f"%{search_text.strip()}%"

    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.id,
                    r.purchase_date,
                    r.store_name,
                    ri.store_item_code,
                    ri.raw_description,
                    ri.quantity,
                    ri.unit_price,
                    ri.total_price
                FROM receipt_items ri
                JOIN receipts r
                    ON r.id = ri.receipt_id
                WHERE ri.raw_description ILIKE %s
                  AND (
                    %s::date IS NULL
                    OR r.purchase_date >= %s::date
                  )
                  AND (
                    %s::date IS NULL
                    OR r.purchase_date <= %s::date
                  )
                ORDER BY
                    r.purchase_date DESC NULLS LAST,
                    r.id DESC,
                    ri.id
                LIMIT %s
                """,
                (
                    search_pattern,
                    start_date,
                    start_date,
                    end_date,
                    end_date,
                    limit,
                ),
            )

            rows = cursor.fetchall()

    return [
        {
            "receipt_id": row[0],
            "purchase_date": row[1],
            "store_name": normalize_store_name(row[2]),
            "store_item_code": row[3],
            "raw_description": row[4],
            "quantity": row[5],
            "unit_price": row[6],
            "total_price": row[7],
        }
        for row in rows
    ]


def get_receipt_detail(receipt_id: int) -> dict | None:
    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    store_name,
                    purchase_date,
                    subtotal,
                    tax,
                    total,
                    transaction_id,
                    source_file
                FROM receipts
                WHERE id = %s
                """,
                (receipt_id,),
            )

            receipt_row = cursor.fetchone()

            if receipt_row is None:
                return None

            cursor.execute(
                """
                SELECT
                    store_item_code,
                    raw_description,
                    quantity,
                    unit_price,
                    total_price
                FROM receipt_items
                WHERE receipt_id = %s
                ORDER BY id
                """,
                (receipt_id,),
            )

            item_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    raw_description,
                    amount,
                    related_item_code
                FROM receipt_discounts
                WHERE receipt_id = %s
                ORDER BY id
                """,
                (receipt_id,),
            )

            discount_rows = cursor.fetchall()

    return {
        "id": receipt_row[0],
        "store_name": normalize_store_name(receipt_row[1]),
        "raw_store_name": receipt_row[1],
        "purchase_date": receipt_row[2],
        "subtotal": receipt_row[3],
        "tax": receipt_row[4],
        "total": receipt_row[5],
        "transaction_id": receipt_row[6],
        "source_file": receipt_row[7],
        "items": [
            {
                "store_item_code": row[0],
                "raw_description": row[1],
                "quantity": row[2],
                "unit_price": row[3],
                "total_price": row[4],
            }
            for row in item_rows
        ],
        "discounts": [
            {
                "raw_description": row[0],
                "amount": row[1],
                "related_item_code": row[2],
            }
            for row in discount_rows
        ],
    }