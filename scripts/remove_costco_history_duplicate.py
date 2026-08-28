from __future__ import annotations

import os
import sys
from decimal import Decimal

import psycopg
from dotenv import load_dotenv


LIVE_RECEIPT_ID = 5
HISTORICAL_RECEIPT_ID = 1500

EXPECTED_DATE = "2025-05-31"
EXPECTED_LIVE_TOTAL = Decimal("116.41")
EXPECTED_HISTORICAL_TOTAL = Decimal("112.59")

EXPECTED_ITEM_CODES = {
    "1495250",
    "384732",
    "1841486",
    "1451835",
    "1794739",
    "1294443",
    "1716914",
    "1055581",
    "3",
    "96716",
}


def get_receipt(
    cur: psycopg.Cursor,
    receipt_id: int,
):
    cur.execute(
        """
        SELECT
            id,
            purchase_date,
            total,
            transaction_id,
            source_type,
            warehouse_number,
            register_number,
            historical_transaction_number,
            historical_key
        FROM receipts
        WHERE id = %s;
        """,
        (receipt_id,),
    )

    return cur.fetchone()


def get_item_codes(
    cur: psycopg.Cursor,
    receipt_id: int,
) -> set[str]:
    cur.execute(
        """
        SELECT store_item_code
        FROM receipt_items
        WHERE receipt_id = %s;
        """,
        (receipt_id,),
    )

    return {
        str(row[0])
        for row in cur.fetchall()
        if row[0] is not None
    }


def get_item_total(
    cur: psycopg.Cursor,
    receipt_id: int,
) -> Decimal:
    cur.execute(
        """
        SELECT COALESCE(
            SUM(total_price),
            0
        )
        FROM receipt_items
        WHERE receipt_id = %s;
        """,
        (receipt_id,),
    )

    return cur.fetchone()[0]


def main() -> None:
    commit_requested = (
        len(sys.argv) == 2
        and sys.argv[1] == "--commit"
    )

    if len(sys.argv) > 2:
        raise SystemExit(
            "Usage: "
            "uv run python "
            "scripts/remove_costco_history_duplicate.py "
            "[--commit]"
        )

    if (
        len(sys.argv) == 2
        and not commit_requested
    ):
        raise SystemExit(
            "Only supported option is --commit."
        )

    load_dotenv()

    database_url = os.getenv(
        "DATABASE_URL"
    )

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured."
        )

    print()
    print("Costco historical duplicate cleanup")
    print("-----------------------------------")

    print(
        "Mode: "
        + (
            "COMMIT"
            if commit_requested
            else "VALIDATION ONLY"
        )
    )

    with psycopg.connect(
        database_url
    ) as conn:
        with conn.cursor() as cur:
            live = get_receipt(
                cur,
                LIVE_RECEIPT_ID,
            )

            historical = get_receipt(
                cur,
                HISTORICAL_RECEIPT_ID,
            )

            if live is None:
                raise RuntimeError(
                    "Expected live receipt "
                    f"id={LIVE_RECEIPT_ID} "
                    "was not found."
                )

            if historical is None:
                raise RuntimeError(
                    "Expected historical receipt "
                    f"id={HISTORICAL_RECEIPT_ID} "
                    "was not found."
                )

            (
                live_id,
                live_date,
                live_total,
                live_transaction_id,
                live_source_type,
                _,
                _,
                _,
                _,
            ) = live

            (
                historical_id,
                historical_date,
                historical_total,
                historical_transaction_id,
                historical_source_type,
                warehouse,
                register,
                transaction_number,
                historical_key,
            ) = historical

            live_codes = get_item_codes(
                cur,
                live_id,
            )

            historical_codes = get_item_codes(
                cur,
                historical_id,
            )

            live_item_total = get_item_total(
                cur,
                live_id,
            )

            historical_item_total = get_item_total(
                cur,
                historical_id,
            )

            print()
            print("Live receipt:")
            print(
                f"- id={live_id}"
                f" | date={live_date}"
                f" | total={live_total}"
                f" | transaction_id="
                f"{live_transaction_id}"
                f" | source_type="
                f"{live_source_type}"
            )

            print()
            print("Historical receipt:")
            print(
                f"- id={historical_id}"
                f" | date={historical_date}"
                f" | total={historical_total}"
                f" | warehouse={warehouse}"
                f" | register={register}"
                f" | transaction="
                f"{transaction_number}"
                f" | source_type="
                f"{historical_source_type}"
            )

            print()
            print("Duplicate validation:")

            checks = {
                "same date": (
                    str(live_date)
                    == EXPECTED_DATE
                    == str(historical_date)
                ),
                "live total expected": (
                    live_total
                    == EXPECTED_LIVE_TOTAL
                ),
                "historical total expected": (
                    historical_total
                    == EXPECTED_HISTORICAL_TOTAL
                ),
                "live item sum equals history total": (
                    live_item_total
                    == EXPECTED_HISTORICAL_TOTAL
                ),
                "historical item sum equals history total": (
                    historical_item_total
                    == EXPECTED_HISTORICAL_TOTAL
                ),
                "live item codes expected": (
                    live_codes
                    == EXPECTED_ITEM_CODES
                ),
                "historical item codes expected": (
                    historical_codes
                    == EXPECTED_ITEM_CODES
                ),
                "same item-code set": (
                    live_codes
                    == historical_codes
                ),
                "live source type": (
                    live_source_type
                    == "live_receipt"
                ),
                "historical source type": (
                    historical_source_type
                    == "costco_shopping_history"
                ),
                "historical key present": (
                    historical_key is not None
                ),
            }

            for name, passed in checks.items():
                print(
                    f"- {name}: "
                    f"{'PASS' if passed else 'FAIL'}"
                )

            if not all(checks.values()):
                raise RuntimeError(
                    "Duplicate validation failed. "
                    "Nothing will be deleted."
                )

            print()
            print(
                "Duplicate validation: PASS"
            )

            if not commit_requested:
                print()
                print(
                    "No database changes performed."
                )

                print(
                    "Rerun with --commit to remove "
                    "historical duplicate id=1500."
                )

                conn.rollback()
                return

            cur.execute(
                """
                SELECT COUNT(*)
                FROM receipt_items
                WHERE receipt_id = %s;
                """,
                (HISTORICAL_RECEIPT_ID,),
            )

            item_count = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*)
                FROM receipt_discounts
                WHERE receipt_id = %s;
                """,
                (HISTORICAL_RECEIPT_ID,),
            )

            discount_count = cur.fetchone()[0]

            print()
            print(
                "Deleting historical duplicate:"
            )

            print(
                f"- item rows: {item_count}"
            )

            print(
                f"- discount rows: "
                f"{discount_count}"
            )

            cur.execute(
                """
                DELETE FROM receipt_discounts
                WHERE receipt_id = %s;
                """,
                (HISTORICAL_RECEIPT_ID,),
            )

            cur.execute(
                """
                DELETE FROM receipt_items
                WHERE receipt_id = %s;
                """,
                (HISTORICAL_RECEIPT_ID,),
            )

            cur.execute(
                """
                DELETE FROM receipts
                WHERE id = %s
                  AND source_type =
                      'costco_shopping_history';
                """,
                (HISTORICAL_RECEIPT_ID,),
            )

            if cur.rowcount != 1:
                raise RuntimeError(
                    "Expected exactly one historical "
                    "receipt to be deleted."
                )

            cur.execute(
                """
                SELECT COUNT(*)
                FROM receipts
                WHERE id = %s;
                """,
                (LIVE_RECEIPT_ID,),
            )

            if cur.fetchone()[0] != 1:
                raise RuntimeError(
                    "Live receipt was unexpectedly "
                    "affected."
                )

            cur.execute(
                """
                SELECT COUNT(*)
                FROM receipts
                WHERE id = %s;
                """,
                (HISTORICAL_RECEIPT_ID,),
            )

            if cur.fetchone()[0] != 0:
                raise RuntimeError(
                    "Historical duplicate still exists."
                )

        conn.commit()

    print()
    print(
        "Historical duplicate removed "
        "successfully."
    )


if __name__ == "__main__":
    main()