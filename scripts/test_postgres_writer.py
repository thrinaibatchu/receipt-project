import os
from datetime import date
from types import SimpleNamespace

import psycopg
from dotenv import load_dotenv

from receipt_project.database.writer import (
    find_receipt_by_source_hash,
    insert_receipt,
)


SOURCE_HASH = (
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)

SECOND_SOURCE_HASH = (
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
)

FINGERPRINT = (
    "cccccccccccccccccccccccccccccccc"
    "cccccccccccccccccccccccccccccccc"
)


def build_test_receipt():
    return SimpleNamespace(
        store_name="POSTGRES WRITER TEST",
        purchase_date=date(2026, 1, 2),
        subtotal=8.00,
        tax=0.64,
        total=8.64,
        transaction_id="TEST-TRANSACTION-001",
        source_file="_postgres_writer_test.pdf",
        items=[
            SimpleNamespace(
                store_item_code="TEST001",
                raw_description="TEST ITEM ONE",
                quantity=1,
                unit_price=5.00,
                total_price=5.00,
            ),
            SimpleNamespace(
                store_item_code="TEST002",
                raw_description="TEST ITEM TWO",
                quantity=1,
                unit_price=4.00,
                total_price=4.00,
            ),
        ],
        discounts=[
            SimpleNamespace(
                raw_description="TEST DISCOUNT",
                amount=1.00,
                related_item_code="TEST002",
            ),
        ],
    )


def cleanup_test_data(database_url: str):
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM receipt_discounts
                WHERE receipt_id IN (
                    SELECT id
                    FROM receipts
                    WHERE source_hash IN (%s, %s)
                )
                """,
                (SOURCE_HASH, SECOND_SOURCE_HASH),
            )

            cursor.execute(
                """
                DELETE FROM receipt_items
                WHERE receipt_id IN (
                    SELECT id
                    FROM receipts
                    WHERE source_hash IN (%s, %s)
                )
                """,
                (SOURCE_HASH, SECOND_SOURCE_HASH),
            )

            cursor.execute(
                """
                DELETE FROM receipts
                WHERE source_hash IN (%s, %s)
                """,
                (SOURCE_HASH, SECOND_SOURCE_HASH),
            )


def main():
    load_dotenv()

    if os.getenv("RECEIPT_DB_BACKEND") != "postgres":
        raise RuntimeError(
            "Run this test with RECEIPT_DB_BACKEND=postgres"
        )

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    receipt = build_test_receipt()

    # Make this test rerunnable.
    cleanup_test_data(database_url)

    try:
        receipt_id = insert_receipt(
            receipt,
            SOURCE_HASH,
            FINGERPRINT,
        )

        print("Postgres receipt insert: SUCCESS")
        print(f"Receipt ID returned: {receipt_id}")

        found = find_receipt_by_source_hash(SOURCE_HASH)

        if not found:
            raise RuntimeError(
                "Inserted receipt could not be found by source_hash"
            )

        print("Postgres source-hash lookup: SUCCESS")

        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM receipt_items
                    WHERE receipt_id = %s
                    """,
                    (receipt_id,),
                )
                item_count = cursor.fetchone()[0]

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM receipt_discounts
                    WHERE receipt_id = %s
                    """,
                    (receipt_id,),
                )
                discount_count = cursor.fetchone()[0]

        if item_count != 2:
            raise RuntimeError(
                f"Expected 2 items, found {item_count}"
            )

        if discount_count != 1:
            raise RuntimeError(
                f"Expected 1 discount, found {discount_count}"
            )

        print("Postgres child-row insert: SUCCESS")
        print(f"Receipt items: {item_count}")
        print(f"Receipt discounts: {discount_count}")

        # Exact-file duplicate test.
        try:
            insert_receipt(
                receipt,
                SOURCE_HASH,
                FINGERPRINT,
            )
        except ValueError:
            print("Postgres source-hash duplicate detection: SUCCESS")
        else:
            raise RuntimeError(
                "Source-hash duplicate was not rejected"
            )

        # Logical duplicate test:
        # different source bytes, same receipt fingerprint.
        try:
            insert_receipt(
                receipt,
                SECOND_SOURCE_HASH,
                FINGERPRINT,
            )
        except ValueError:
            print(
                "Postgres logical duplicate detection: SUCCESS"
            )
        else:
            raise RuntimeError(
                "Receipt-fingerprint duplicate was not rejected"
            )

    finally:
        cleanup_test_data(database_url)

    print("Postgres test cleanup: SUCCESS")


if __name__ == "__main__":
    main()
