import sqlite3
from pathlib import Path


DB_PATH = Path("data/receipts.db")

SAMPLE_SOURCE_FILE = "sample_costco_receipt.jpg"


def insert_sample_receipt() -> None:
    connection = sqlite3.connect(DB_PATH)

    # SQLite does not enforce foreign keys by default
    connection.execute("PRAGMA foreign_keys = ON")

    # Prevent us from accidentally inserting the sample twice
    existing_receipt = connection.execute(
        """
        SELECT id
        FROM receipts
        WHERE source_file = ?
        """,
        (SAMPLE_SOURCE_FILE,),
    ).fetchone()

    if existing_receipt:
        print(
            f"Sample receipt already exists with id={existing_receipt[0]}"
        )
        connection.close()
        return

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
            "Costco",
            "2026-08-15",
            29.02,
            0.00,
            29.02,
            SAMPLE_SOURCE_FILE,
        ),
    )

    receipt_id = cursor.lastrowid

    items = [
        (
            receipt_id,
            None,
            "KS ORG EGGS 24CT",
            1,
            7.99,
            7.99,
        ),
        (
            receipt_id,
            None,
            "MILK 2% GAL",
            2,
            4.29,
            8.58,
        ),
        (
            receipt_id,
            None,
            "BANANAS",
            1,
            1.49,
            1.49,
        ),
        (
            receipt_id,
            None,
            "KS BREAD 2PK",
            1,
            10.96,
            10.96,
        ),
    ]

    connection.executemany(
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
        items,
    )

    connection.commit()
    connection.close()

    print(f"Inserted sample Costco receipt with id={receipt_id}")


if __name__ == "__main__":
    insert_sample_receipt()
