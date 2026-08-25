import os

import psycopg
from dotenv import load_dotenv

from receipt_project.models.receipt import Receipt


def _get_database_url() -> str:
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required when "
            "RECEIPT_DB_BACKEND=postgres"
        )

    return database_url


def find_receipt_by_source_hash(source_hash: str):
    with psycopg.connect(_get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    source_file
                FROM receipts
                WHERE source_hash = %s
                """,
                (source_hash,),
            )

            return cursor.fetchone()


def insert_receipt(
    receipt: Receipt,
    source_hash: str,
    receipt_fingerprint: str | None,
) -> int:
    with psycopg.connect(_get_database_url()) as connection:
        try:
            with connection.cursor() as cursor:
                # Detect either:
                # 1. the exact same source file, or
                # 2. the same logical receipt extracted from another file
                cursor.execute(
                    """
                    SELECT
                        id,
                        source_file
                    FROM receipts
                    WHERE source_hash = %s
                    OR (
                        receipt_fingerprint IS NOT NULL
                        AND receipt_fingerprint = %s
                    )
                    """,
                    (
                        source_hash,
                        receipt_fingerprint,
                    ),
                )

                existing = cursor.fetchone()

                if existing:
                    raise ValueError(
                        "Duplicate receipt detected. "
                        f"Existing receipt id={existing[0]}, "
                        f"source_file={existing[1]}"
                    )

                cursor.execute(
                    """
                    INSERT INTO receipts (
                        store_name,
                        purchase_date,
                        subtotal,
                        tax,
                        total,
                        transaction_id,
                        source_file,
                        source_hash,
                        receipt_fingerprint
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    RETURNING id
                    """,
                    (
                        receipt.store_name,
                        receipt.purchase_date,
                        receipt.subtotal,
                        receipt.tax,
                        receipt.total,
                        receipt.transaction_id,
                        receipt.source_file,
                        source_hash,
                        receipt_fingerprint,
                    ),
                )

                receipt_id = cursor.fetchone()[0]

                for item in receipt.items:
                    cursor.execute(
                        """
                        INSERT INTO receipt_items (
                            receipt_id,
                            product_id,
                            store_item_code,
                            raw_description,
                            quantity,
                            unit_price,
                            total_price
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            receipt_id,
                            None,
                            item.store_item_code,
                            item.raw_description,
                            item.quantity,
                            item.unit_price,
                            item.total_price,
                        ),
                    )

                for discount in receipt.discounts:
                    cursor.execute(
                        """
                        INSERT INTO receipt_discounts (
                            receipt_id,
                            raw_description,
                            amount,
                            related_item_code
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            receipt_id,
                            discount.raw_description,
                            discount.amount,
                            discount.related_item_code,
                        ),
                    )

            connection.commit()
            return receipt_id

        except Exception:
            connection.rollback()
            raise
