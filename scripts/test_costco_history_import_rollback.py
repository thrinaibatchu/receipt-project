from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from receipt_project.history.costco_transform import (
    HistoricalReceipt,
    build_historical_receipts,
)


EXPECTED_RECEIPTS = 800
EXPECTED_ITEMS = 3338
EXPECTED_DISCOUNTS = 381


def build_transaction_id(
    receipt: HistoricalReceipt,
) -> str:
    return (
        "costco-history:"
        f"{receipt.warehouse_number}:"
        f"{receipt.purchase_date.isoformat()}:"
        f"{receipt.register_number}:"
        f"{receipt.historical_transaction_number}"
    )


def get_database_counts(
    conn: psycopg.Connection,
) -> tuple[int, int, int, int]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM receipts;
            """
        )
        receipt_count = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COUNT(*)
            FROM receipt_items;
            """
        )
        item_count = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COUNT(*)
            FROM receipt_discounts;
            """
        )
        discount_count = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COUNT(*)
            FROM receipts
            WHERE source_type = 'costco_shopping_history';
            """
        )
        historical_receipt_count = cur.fetchone()[0]

    return (
        receipt_count,
        item_count,
        discount_count,
        historical_receipt_count,
    )


def verify_no_existing_historical_keys(
    conn: psycopg.Connection,
    receipts: list[HistoricalReceipt],
) -> None:
    historical_keys = [
        receipt.historical_key
        for receipt in receipts
    ]

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT historical_key
            FROM receipts
            WHERE historical_key = ANY(%s);
            """,
            (historical_keys,),
        )

        collisions = [
            row[0]
            for row in cur.fetchall()
        ]

    if collisions:
        preview = ", ".join(
            key[:12]
            for key in collisions[:10]
        )

        raise RuntimeError(
            "Historical import cannot proceed because "
            f"{len(collisions)} historical keys already "
            f"exist in Neon. Examples: {preview}"
        )


def insert_historical_receipt(
    conn: psycopg.Connection,
    receipt: HistoricalReceipt,
) -> int:
    transaction_id = build_transaction_id(
        receipt
    )

    with conn.cursor() as cur:
        cur.execute(
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
                receipt_fingerprint,
                source_type,
                warehouse_number,
                register_number,
                historical_transaction_number,
                transaction_time,
                historical_key
            )
            VALUES (
                %s,
                %s,
                NULL,
                NULL,
                %s,
                %s,
                %s,
                NULL,
                NULL,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING id;
            """,
            (
                receipt.store_name,
                receipt.purchase_date,
                receipt.calculated_total,
                transaction_id,
                receipt.source_file,
                receipt.source_type,
                receipt.warehouse_number,
                receipt.register_number,
                receipt.historical_transaction_number,
                receipt.transaction_time,
                receipt.historical_key,
            ),
        )

        receipt_id = cur.fetchone()[0]

        for item in receipt.items:
            cur.execute(
                """
                INSERT INTO receipt_items (
                    receipt_id,
                    product_id,
                    store_item_code,
                    raw_description,
                    quantity,
                    unit_price,
                    total_price,
                    source_row_number,
                    historical_row_type
                )
                VALUES (
                    %s,
                    NULL,
                    %s,
                    %s,
                    %s,
                    NULL,
                    %s,
                    %s,
                    %s
                );
                """,
                (
                    receipt_id,
                    item.store_item_code,
                    item.raw_description,
                    item.quantity,
                    item.total_price,
                    item.source_row_number,
                    item.historical_row_type,
                ),
            )

        for discount in receipt.discounts:
            cur.execute(
                """
                INSERT INTO receipt_discounts (
                    receipt_id,
                    raw_description,
                    amount,
                    related_item_code,
                    source_row_number,
                    historical_row_type
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                );
                """,
                (
                    receipt_id,
                    discount.raw_description,
                    discount.amount,
                    discount.related_item_code,
                    discount.source_row_number,
                    discount.historical_row_type,
                ),
            )

    return receipt_id


def verify_inserted_history(
    conn: psycopg.Connection,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM receipts
            WHERE source_type = 'costco_shopping_history';
            """
        )

        historical_receipts = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COUNT(*)
            FROM receipt_items ri
            JOIN receipts r
              ON r.id = ri.receipt_id
            WHERE r.source_type = 'costco_shopping_history';
            """
        )

        historical_items = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COUNT(*)
            FROM receipt_discounts rd
            JOIN receipts r
              ON r.id = rd.receipt_id
            WHERE r.source_type = 'costco_shopping_history';
            """
        )

        historical_discounts = cur.fetchone()[0]

        cur.execute(
            """
            SELECT
                COUNT(*),
                COUNT(DISTINCT historical_key)
            FROM receipts
            WHERE source_type = 'costco_shopping_history';
            """
        )

        (
            total_historical_keys,
            distinct_historical_keys,
        ) = cur.fetchone()

        cur.execute(
            """
            SELECT
                COUNT(*)
            FROM receipts
            WHERE source_type = 'costco_shopping_history'
              AND historical_key IS NULL;
            """
        )

        missing_historical_keys = (
            cur.fetchone()[0]
        )

        cur.execute(
            """
            SELECT
                COUNT(*)
            FROM receipts
            WHERE source_type = 'costco_shopping_history'
              AND source_hash IS NOT NULL;
            """
        )

        historical_rows_with_source_hash = (
            cur.fetchone()[0]
        )

        cur.execute(
            """
            SELECT
                COALESCE(SUM(total), 0)
            FROM receipts
            WHERE source_type = 'costco_shopping_history';
            """
        )

        historical_net_total = (
            cur.fetchone()[0]
        )

        cur.execute(
            """
            SELECT
                historical_row_type,
                COUNT(*)
            FROM receipt_items ri
            JOIN receipts r
              ON r.id = ri.receipt_id
            WHERE r.source_type = 'costco_shopping_history'
            GROUP BY historical_row_type
            ORDER BY historical_row_type;
            """
        )

        item_type_counts = dict(
            cur.fetchall()
        )

        cur.execute(
            """
            SELECT
                historical_row_type,
                COUNT(*)
            FROM receipt_discounts rd
            JOIN receipts r
              ON r.id = rd.receipt_id
            WHERE r.source_type = 'costco_shopping_history'
            GROUP BY historical_row_type
            ORDER BY historical_row_type;
            """
        )

        discount_type_counts = dict(
            cur.fetchall()
        )

    print()
    print("Inside-transaction verification")
    print("-------------------------------")

    print(
        f"Historical receipts: "
        f"{historical_receipts}"
    )

    print(
        f"Historical receipt items: "
        f"{historical_items}"
    )

    print(
        f"Historical receipt discounts: "
        f"{historical_discounts}"
    )

    print(
        "Historical keys: "
        f"{total_historical_keys}"
    )

    print(
        "Distinct historical keys: "
        f"{distinct_historical_keys}"
    )

    print(
        "Missing historical keys: "
        f"{missing_historical_keys}"
    )

    print(
        "Historical rows with source_hash: "
        f"{historical_rows_with_source_hash}"
    )

    print(
        "Historical calculated net total: "
        f"{historical_net_total}"
    )

    print()
    print("Historical item types:")

    for row_type in (
        "purchase",
        "return",
        "adjustment",
    ):
        print(
            f"- {row_type}: "
            f"{item_type_counts.get(row_type, 0)}"
        )

    print()
    print("Historical discount types:")

    for row_type in (
        "coupon_discount",
        "coupon_reversal",
        "coupon_adjustment",
    ):
        print(
            f"- {row_type}: "
            f"{discount_type_counts.get(row_type, 0)}"
        )

    if historical_receipts != EXPECTED_RECEIPTS:
        raise RuntimeError(
            "Unexpected historical receipt count: "
            f"{historical_receipts}"
        )

    if historical_items != EXPECTED_ITEMS:
        raise RuntimeError(
            "Unexpected historical item count: "
            f"{historical_items}"
        )

    if historical_discounts != EXPECTED_DISCOUNTS:
        raise RuntimeError(
            "Unexpected historical discount count: "
            f"{historical_discounts}"
        )

    if total_historical_keys != EXPECTED_RECEIPTS:
        raise RuntimeError(
            "Unexpected historical key count."
        )

    if (
        distinct_historical_keys
        != EXPECTED_RECEIPTS
    ):
        raise RuntimeError(
            "Historical keys are not unique."
        )

    if missing_historical_keys != 0:
        raise RuntimeError(
            "Historical rows are missing "
            "historical_key values."
        )

    if historical_rows_with_source_hash != 0:
        raise RuntimeError(
            "Historical rows unexpectedly contain "
            "live receipt source hashes."
        )

    if historical_net_total != Decimal(
        "39703.04"
    ):
        raise RuntimeError(
            "Unexpected historical net total: "
            f"{historical_net_total}"
        )

    expected_item_types = {
        "purchase": 3033,
        "return": 295,
        "adjustment": 10,
    }

    if item_type_counts != expected_item_types:
        raise RuntimeError(
            "Historical item type counts "
            "do not match dry-run results. "
            f"Actual: {item_type_counts}"
        )

    expected_discount_types = {
        "coupon_discount": 306,
        "coupon_reversal": 74,
        "coupon_adjustment": 1,
    }

    if (
        discount_type_counts
        != expected_discount_types
    ):
        raise RuntimeError(
            "Historical discount type counts "
            "do not match dry-run results. "
            f"Actual: {discount_type_counts}"
        )

    print()
    print(
        "Inside-transaction verification: PASS"
    )


def verify_after_rollback(
    database_url: str,
    before_counts: tuple[int, int, int, int],
) -> None:
    with psycopg.connect(
        database_url
    ) as conn:
        after_counts = get_database_counts(
            conn
        )

    print()
    print("Post-rollback verification")
    print("--------------------------")

    print(
        f"Receipts before: "
        f"{before_counts[0]}"
    )

    print(
        f"Receipts after: "
        f"{after_counts[0]}"
    )

    print(
        f"Receipt items before: "
        f"{before_counts[1]}"
    )

    print(
        f"Receipt items after: "
        f"{after_counts[1]}"
    )

    print(
        f"Receipt discounts before: "
        f"{before_counts[2]}"
    )

    print(
        f"Receipt discounts after: "
        f"{after_counts[2]}"
    )

    print(
        "Historical receipts after rollback: "
        f"{after_counts[3]}"
    )

    if after_counts != before_counts:
        raise RuntimeError(
            "Database counts changed despite rollback. "
            f"Before={before_counts}, "
            f"after={after_counts}"
        )

    if after_counts[3] != 0:
        raise RuntimeError(
            "Historical rows remain after rollback."
        )

    print()
    print(
        "Post-rollback verification: PASS"
    )


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: "
            "uv run python "
            "scripts/test_costco_history_import_rollback.py "
            "<costco-history.pdf>"
        )

    load_dotenv()

    database_url = os.getenv(
        "DATABASE_URL"
    )

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured."
        )

    pdf_path = Path(
        sys.argv[1]
    ).expanduser()

    print()
    print("Costco historical rollback import test")
    print("--------------------------------------")

    print(
        f"Source: {pdf_path.name}"
    )

    print()
    print(
        "Parsing and transforming "
        "historical statement..."
    )

    receipts = (
        build_historical_receipts(
            pdf_path
        )
    )

    transformed_items = sum(
        len(receipt.items)
        for receipt in receipts
    )

    transformed_discounts = sum(
        len(receipt.discounts)
        for receipt in receipts
    )

    print(
        f"Transformed receipts: "
        f"{len(receipts)}"
    )

    print(
        f"Transformed items: "
        f"{transformed_items}"
    )

    print(
        f"Transformed discounts: "
        f"{transformed_discounts}"
    )

    if len(receipts) != EXPECTED_RECEIPTS:
        raise RuntimeError(
            "Unexpected transformed "
            "receipt count."
        )

    if transformed_items != EXPECTED_ITEMS:
        raise RuntimeError(
            "Unexpected transformed "
            "item count."
        )

    if (
        transformed_discounts
        != EXPECTED_DISCOUNTS
    ):
        raise RuntimeError(
            "Unexpected transformed "
            "discount count."
        )

    with psycopg.connect(
        database_url
    ) as conn:
        before_counts = (
            get_database_counts(
                conn
            )
        )

        print()
        print("Database before test")
        print("--------------------")

        print(
            f"Receipts: "
            f"{before_counts[0]}"
        )

        print(
            f"Receipt items: "
            f"{before_counts[1]}"
        )

        print(
            f"Receipt discounts: "
            f"{before_counts[2]}"
        )

        print(
            "Historical receipts: "
            f"{before_counts[3]}"
        )

        if before_counts[3] != 0:
            raise RuntimeError(
                "Historical receipts already "
                "exist in Neon. Rollback test "
                "aborted."
            )

        verify_no_existing_historical_keys(
            conn,
            receipts,
        )

        print()
        print(
            "Historical key collision check: PASS"
        )

        print()
        print(
            "Inserting historical dataset "
            "inside rollback transaction..."
        )

        try:
            for index, receipt in enumerate(
                receipts,
                start=1,
            ):
                insert_historical_receipt(
                    conn,
                    receipt,
                )

                if index % 100 == 0:
                    print(
                        f"- inserted "
                        f"{index}/"
                        f"{len(receipts)} "
                        "transactions"
                    )

            verify_inserted_history(
                conn
            )

            print()
            print(
                "All insert checks passed."
            )

        finally:
            print()
            print(
                "Rolling back historical import..."
            )

            conn.rollback()

            print(
                "Rollback executed."
            )

    verify_after_rollback(
        database_url,
        before_counts,
    )

    print()
    print(
        "Costco historical rollback "
        "import test: PASS"
    )


if __name__ == "__main__":
    main()