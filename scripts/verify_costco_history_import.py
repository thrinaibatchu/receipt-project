from __future__ import annotations

import os
from decimal import Decimal

import psycopg
from dotenv import load_dotenv


EXPECTED_TOTAL_RECEIPTS = 803
EXPECTED_LIVE_RECEIPTS = 4
EXPECTED_HISTORICAL_RECEIPTS = 799

EXPECTED_TOTAL_ITEMS = 3359
EXPECTED_HISTORICAL_ITEMS = 3328

EXPECTED_TOTAL_DISCOUNTS = 384
EXPECTED_HISTORICAL_DISCOUNTS = 381

EXPECTED_HISTORICAL_NET = Decimal(
    "39590.45"
)

EXPECTED_ITEM_TYPES = {
    "purchase": 3023,
    "return": 295,
    "adjustment": 10,
}

EXPECTED_DISCOUNT_TYPES = {
    "coupon_discount": 306,
    "coupon_reversal": 74,
    "coupon_adjustment": 1,
}

EXPECTED_MIN_DATE = "2019-05-09"
EXPECTED_MAX_DATE = "2026-06-08"


def main() -> None:
    load_dotenv()

    database_url = os.getenv(
        "DATABASE_URL"
    )

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured."
        )

    with psycopg.connect(
        database_url
    ) as conn:
        with conn.cursor() as cur:
            print()
            print(
                "Costco historical import verification"
            )
            print(
                "-------------------------------------"
            )

            cur.execute(
                """
                SELECT COUNT(*)
                FROM receipts;
                """
            )
            total_receipts = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*)
                FROM receipts
                WHERE source_type = 'live_receipt';
                """
            )
            live_receipts = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*)
                FROM receipts
                WHERE source_type =
                    'costco_shopping_history';
                """
            )
            historical_receipts = (
                cur.fetchone()[0]
            )

            cur.execute(
                """
                SELECT COUNT(*)
                FROM receipt_items;
                """
            )
            total_items = cur.fetchone()[0]

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
            historical_items = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*)
                FROM receipt_discounts;
                """
            )
            total_discounts = cur.fetchone()[0]

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
            historical_discounts = (
                cur.fetchone()[0]
            )

            cur.execute(
                """
                SELECT
                    COUNT(historical_key),
                    COUNT(DISTINCT historical_key)
                FROM receipts
                WHERE source_type =
                    'costco_shopping_history';
                """
            )

            (
                historical_keys,
                distinct_historical_keys,
            ) = cur.fetchone()

            cur.execute(
                """
                SELECT COALESCE(
                    SUM(total),
                    0
                )
                FROM receipts
                WHERE source_type =
                    'costco_shopping_history';
                """
            )
            historical_net = cur.fetchone()[0]

            cur.execute(
                """
                SELECT
                    MIN(purchase_date),
                    MAX(purchase_date)
                FROM receipts
                WHERE source_type =
                    'costco_shopping_history';
                """
            )

            (
                min_date,
                max_date,
            ) = cur.fetchone()

            cur.execute(
                """
                SELECT
                    historical_row_type,
                    COUNT(*)
                FROM receipt_items ri
                JOIN receipts r
                  ON r.id = ri.receipt_id
                WHERE r.source_type =
                    'costco_shopping_history'
                GROUP BY historical_row_type
                ORDER BY historical_row_type;
                """
            )
            item_types = dict(
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
                WHERE r.source_type =
                    'costco_shopping_history'
                GROUP BY historical_row_type
                ORDER BY historical_row_type;
                """
            )
            discount_types = dict(
                cur.fetchall()
            )

            cur.execute(
                """
                SELECT COUNT(*)
                FROM receipts
                WHERE source_type =
                    'costco_shopping_history'
                  AND historical_key IS NULL;
                """
            )
            missing_historical_keys = (
                cur.fetchone()[0]
            )

            cur.execute(
                """
                SELECT COUNT(*)
                FROM receipts
                WHERE source_type =
                    'costco_shopping_history'
                  AND source_hash IS NOT NULL;
                """
            )
            historical_rows_with_source_hash = (
                cur.fetchone()[0]
            )

    print(
        f"Total receipts: {total_receipts}"
    )

    print(
        f"Live receipts: {live_receipts}"
    )

    print(
        f"Historical receipts: "
        f"{historical_receipts}"
    )

    print()
    print(
        f"Total receipt items: "
        f"{total_items}"
    )

    print(
        f"Historical receipt items: "
        f"{historical_items}"
    )

    print()
    print(
        f"Total receipt discounts: "
        f"{total_discounts}"
    )

    print(
        f"Historical receipt discounts: "
        f"{historical_discounts}"
    )

    print()
    print(
        f"Historical keys: "
        f"{historical_keys}"
    )

    print(
        f"Distinct historical keys: "
        f"{distinct_historical_keys}"
    )

    print(
        f"Missing historical keys: "
        f"{missing_historical_keys}"
    )

    print(
        "Historical rows with source_hash: "
        f"{historical_rows_with_source_hash}"
    )

    print(
        f"Historical net total: "
        f"{historical_net}"
    )

    print(
        f"Historical date range: "
        f"{min_date} -> {max_date}"
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
            f"{item_types.get(row_type, 0)}"
        )

    print()
    print(
        "Historical discount types:"
    )

    for row_type in (
        "coupon_discount",
        "coupon_reversal",
        "coupon_adjustment",
    ):
        print(
            f"- {row_type}: "
            f"{discount_types.get(row_type, 0)}"
        )

    failures: list[str] = []

    if (
        total_receipts
        != EXPECTED_TOTAL_RECEIPTS
    ):
        failures.append(
            "Total receipt count mismatch."
        )

    if (
        live_receipts
        != EXPECTED_LIVE_RECEIPTS
    ):
        failures.append(
            "Live receipt count mismatch."
        )

    if (
        historical_receipts
        != EXPECTED_HISTORICAL_RECEIPTS
    ):
        failures.append(
            "Historical receipt count mismatch."
        )

    if (
        total_items
        != EXPECTED_TOTAL_ITEMS
    ):
        failures.append(
            "Total receipt item count mismatch."
        )

    if (
        historical_items
        != EXPECTED_HISTORICAL_ITEMS
    ):
        failures.append(
            "Historical item count mismatch."
        )

    if (
        total_discounts
        != EXPECTED_TOTAL_DISCOUNTS
    ):
        failures.append(
            "Total receipt discount count mismatch."
        )

    if (
        historical_discounts
        != EXPECTED_HISTORICAL_DISCOUNTS
    ):
        failures.append(
            "Historical discount count mismatch."
        )

    if (
        historical_keys
        != EXPECTED_HISTORICAL_RECEIPTS
    ):
        failures.append(
            "Historical key count mismatch."
        )

    if (
        distinct_historical_keys
        != EXPECTED_HISTORICAL_RECEIPTS
    ):
        failures.append(
            "Historical keys are not unique."
        )

    if missing_historical_keys != 0:
        failures.append(
            "Historical receipts are missing keys."
        )

    if (
        historical_rows_with_source_hash
        != 0
    ):
        failures.append(
            "Historical receipts unexpectedly "
            "contain source_hash."
        )

    if (
        historical_net
        != EXPECTED_HISTORICAL_NET
    ):
        failures.append(
            "Historical net total mismatch."
        )

    if str(min_date) != EXPECTED_MIN_DATE:
        failures.append(
            "Historical minimum date mismatch."
        )

    if str(max_date) != EXPECTED_MAX_DATE:
        failures.append(
            "Historical maximum date mismatch."
        )

    if item_types != EXPECTED_ITEM_TYPES:
        failures.append(
            "Historical item type "
            f"counts mismatch: {item_types}"
        )

    if (
        discount_types
        != EXPECTED_DISCOUNT_TYPES
    ):
        failures.append(
            "Historical discount type "
            f"counts mismatch: {discount_types}"
        )

    print()

    if failures:
        print(
            "Historical import verification: FAIL"
        )

        for failure in failures:
            print(
                f"- {failure}"
            )

        raise RuntimeError(
            "Historical import verification failed."
        )

    print(
        "Historical import verification: PASS"
    )


if __name__ == "__main__":
    main()