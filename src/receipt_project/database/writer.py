import sqlite3
from pathlib import Path

from receipt_project.models.receipt import Receipt


DB_PATH = Path("data/receipts.db")


def insert_receipt(receipt: Receipt) -> int:
    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        existing = connection.execute(
            """
            SELECT id
            FROM receipts
            WHERE source_file = ?
            """,
            (receipt.source_file,),
        ).fetchone()

        if existing:
            raise ValueError(
                f"Receipt already exists with id={existing[0]}"
            )

        cursor = connection.execute(
            """
            INSERT INTO receipts (
                store_name,
                purchase_date,
                subtotal,
                tax,
                total,
                source_file
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                receipt.store_name,
                receipt.purchase_date.isoformat(),
                receipt.subtotal,
                receipt.tax,
                receipt.total,
                receipt.source_file,
            ),
        )

        receipt_id = cursor.lastrowid

        for item in receipt.items:
            connection.execute(
                """
                INSERT INTO receipt_items (
                    receipt_id,
                    product_id,
                    raw_description,
                    quantity,
                    unit_price,
                    total_price
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_id,
                    None,
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
                    discount.related_item_code
                ),
            )
        connection.commit()

        return receipt_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
