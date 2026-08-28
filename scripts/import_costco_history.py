from __future__ import annotations

import argparse
import os
from decimal import Decimal
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from receipt_project.history.costco_import import (
    find_existing_historical_keys,
    insert_historical_receipt,
)
from receipt_project.history.costco_transform import (
    build_historical_receipts,
)


EXPECTED_RECEIPTS = 800
EXPECTED_ITEMS = 3338
EXPECTED_DISCOUNTS = 381
EXPECTED_NET_TOTAL = Decimal("39703.04")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import Costco shopping-history "
            "transactions into Neon."
        )
    )

    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to Costco shopping history PDF.",
    )

    parser.add_argument(
        "--commit",
        action="store_true",
        help=(
            "Actually commit the historical import. "
            "Without this flag, no database writes occur."
        ),
    )

    return parser.parse_args()


def verify_transformation(
    receipts,
) -> None:
    item_count = sum(
        len(receipt.items)
        for receipt in receipts
    )

    discount_count = sum(
        len(receipt.discounts)
        for receipt in receipts
    )

    net_total = sum(
        (
            receipt.calculated_total
            for receipt in receipts
        ),
        Decimal("0"),
    )

    historical_keys = [
        receipt.historical_key
        for receipt in receipts
    ]

    print()
    print("Transformation verification")
    print("---------------------------")

    print(
        f"Receipts: {len(receipts)}"
    )

    print(
        f"Items: {item_count}"
    )

    print(
        f"Discounts: {discount_count}"
    )

    print(
        f"Distinct historical keys: "
        f"{len(set(historical_keys))}"
    )

    print(
        f"Calculated net total: "
        f"{net_total}"
    )

    if len(receipts) != EXPECTED_RECEIPTS:
        raise RuntimeError(
            "Unexpected transformed receipt count."
        )

    if item_count != EXPECTED_ITEMS:
        raise RuntimeError(
            "Unexpected transformed item count."
        )

    if discount_count != EXPECTED_DISCOUNTS:
        raise RuntimeError(
            "Unexpected transformed discount count."
        )

    if (
        len(set(historical_keys))
        != EXPECTED_RECEIPTS
    ):
        raise RuntimeError(
            "Historical keys are not unique."
        )

    if net_total != EXPECTED_NET_TOTAL:
        raise RuntimeError(
            "Unexpected historical net total: "
            f"{net_total}"
        )

    print()
    print(
        "Transformation verification: PASS"
    )


def verify_inside_transaction(
    conn: psycopg.Connection,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM receipts
            WHERE source_type =
                'costco_shopping_history';
            """
        )

        receipt_count = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COUNT(*)
            FROM receipt_items ri
            JOIN receipts r
              ON r.id = ri.receipt_id
            WHERE r.source_type =
                'costco_shopping_history';
            """
        )

        item_count = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COUNT(*)
            FROM receipt_discounts rd
            JOIN receipts r
              ON r.id = rd.receipt_id
            WHERE r.source_type =
                'costco_shopping_history';
            """
        )

        discount_count = cur.fetchone()[0]

        cur.execute(
            """
            SELECT
                COUNT(*),
                COUNT(DISTINCT historical_key),
                COALESCE(SUM(total), 0)
            FROM receipts
            WHERE source_type =
                'costco_shopping_history';
            """
        )

        (
            key_count,
            distinct_key_count,
            net_total,
        ) = cur.fetchone()

        cur.execute(
            """
            SELECT COUNT(*)
            FROM receipts
            WHERE source_type =
                'costco_shopping_history'
              AND historical_key IS NULL;
            """
        )

        missing_keys = cur.fetchone()[0]

        cur.execute(
            """
            SELECT COUNT(*)
            FROM receipts
            WHERE source_type =
                'costco_shopping_history'
              AND source_hash IS NOT NULL;
            """
        )

        rows_with_source_hash = (
            cur.fetchone()[0]
        )

    print()
    print("Pre-commit database verification")
    print("--------------------------------")

    print(
        f"Historical receipts: "
        f"{receipt_count}"
    )

    print(
        f"Historical items: "
        f"{item_count}"
    )

    print(
        f"Historical discounts: "
        f"{discount_count}"
    )

    print(
        f"Historical keys: "
        f"{key_count}"
    )

    print(
        f"Distinct historical keys: "
        f"{distinct_key_count}"
    )

    print(
        f"Missing historical keys: "
        f"{missing_keys}"
    )

    print(
        f"Rows with source_hash: "
        f"{rows_with_source_hash}"
    )

    print(
        f"Historical net total: "
        f"{net_total}"
    )

    if receipt_count != EXPECTED_RECEIPTS:
        raise RuntimeError(
            "Historical receipt count mismatch."
        )

    if item_count != EXPECTED_ITEMS:
        raise RuntimeError(
            "Historical item count mismatch."
        )

    if discount_count != EXPECTED_DISCOUNTS:
        raise RuntimeError(
            "Historical discount count mismatch."
        )

    if key_count != EXPECTED_RECEIPTS:
        raise RuntimeError(
            "Historical key count mismatch."
        )

    if distinct_key_count != EXPECTED_RECEIPTS:
        raise RuntimeError(
            "Historical keys are not unique."
        )

    if missing_keys != 0:
        raise RuntimeError(
            "Historical receipts are missing keys."
        )

    if rows_with_source_hash != 0:
        raise RuntimeError(
            "Historical receipts unexpectedly "
            "contain source_hash."
        )

    if net_total != EXPECTED_NET_TOTAL:
        raise RuntimeError(
            "Historical net total mismatch: "
            f"{net_total}"
        )

    print()
    print(
        "Pre-commit database verification: PASS"
    )


def main() -> None:
    args = parse_args()

    load_dotenv()

    database_url = os.getenv(
        "DATABASE_URL"
    )

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured."
        )

    pdf_path = (
        args.pdf_path
        .expanduser()
        .resolve()
    )

    print()
    print("Costco historical importer")
    print("--------------------------")

    print(
        f"Source: {pdf_path.name}"
    )

    print(
        "Mode: "
        + (
            "COMMIT"
            if args.commit
            else "VALIDATION ONLY"
        )
    )

    print()
    print(
        "Parsing and transforming source..."
    )

    receipts = (
        build_historical_receipts(
            pdf_path
        )
    )

    verify_transformation(
        receipts
    )

    if not args.commit:
        print()
        print(
            "No database writes performed."
        )

        print(
            "To perform the permanent import, "
            "rerun with --commit."
        )

        return

    with psycopg.connect(
        database_url
    ) as conn:
        collisions = (
            find_existing_historical_keys(
                conn,
                receipts,
            )
        )

        if collisions:
            print()
            print(
                "Historical key collision check: FAIL"
            )

            print(
                f"Existing historical keys: "
                f"{len(collisions)}"
            )

            for key in collisions[:10]:
                print(
                    f"- {key[:12]}"
                )

            raise RuntimeError(
                "Historical import aborted. "
                "One or more transactions "
                "already exist."
            )

        print()
        print(
            "Historical key collision check: PASS"
        )

        print()
        print(
            "Beginning permanent historical import..."
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

            verify_inside_transaction(
                conn
            )

            print()
            print(
                "Committing historical import..."
            )

            conn.commit()

        except Exception:
            conn.rollback()

            print()
            print(
                "Import failed. "
                "Transaction rolled back."
            )

            raise

    print()
    print(
        "Historical import committed successfully."
    )


if __name__ == "__main__":
    main()