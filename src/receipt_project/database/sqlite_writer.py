import sqlite3
from pathlib import Path

from receipt_project.models.receipt import Receipt


DB_PATH = Path("data/receipts.db")

def find_receipt_by_source_hash(source_hash: str):
    connection = sqlite3.connect(DB_PATH)

    try:
        return connection.execute(
            """
            SELECT
                id,
                source_file
            FROM receipts
            WHERE source_hash = ?
            """,
            (source_hash,),
        ).fetchone()

    finally:
        connection.close()

def insert_receipt(
    receipt: Receipt,
    source_hash: str,
    receipt_fingerprint: str | None,
) -> int:
    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        # Detect either:
        # 1. the exact same source file, or
        # 2. the same logical receipt extracted from another file
        existing = connection.execute(
            """
            SELECT
                id,
                source_file
            FROM receipts
            WHERE source_hash = ?
            OR (
                    receipt_fingerprint IS NOT NULL
                    AND receipt_fingerprint = ?
            )
            """,
            (
                source_hash,
                receipt_fingerprint,
            ),
        ).fetchone()

        if existing:
            raise ValueError(
                "Duplicate receipt detected. "
                f"Existing receipt id={existing[0]}, "
                f"source_file={existing[1]}"
            )

        cursor = connection.execute(
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt.store_name,
                receipt.purchase_date.isoformat()
                if receipt.purchase_date
                else None,
                receipt.subtotal,
                receipt.tax,
                receipt.total,
                receipt.transaction_id,
                receipt.source_file,
                source_hash,
                receipt_fingerprint,
            ),
        )

        receipt_id = cursor.lastrowid

        for item in receipt.items:
            connection.execute(
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
                VALUES (?, ?, ?, ?, ?, ?, ?)
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
            connection.execute(
                """
                INSERT INTO receipt_discounts (
                    receipt_id,
                    raw_description,
                    amount,
                    related_item_code
                )
                VALUES (?, ?, ?, ?)
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

    finally:
        connection.close()