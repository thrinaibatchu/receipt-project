from __future__ import annotations

import os

import psycopg
from dotenv import load_dotenv


LIVE_RECEIPT_ID = 5


def main() -> None:
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured."
        )

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            print()
            print("Costco live/historical overlap check")
            print("-----------------------------------")

            cur.execute(
                """
                SELECT
                    id,
                    store_name,
                    purchase_date,
                    total,
                    transaction_id,
                    source_type
                FROM receipts
                WHERE id = %s;
                """,
                (LIVE_RECEIPT_ID,),
            )

            live_receipt = cur.fetchone()

            if live_receipt is None:
                raise RuntimeError(
                    f"Live receipt id={LIVE_RECEIPT_ID} "
                    "was not found."
                )

            (
                live_id,
                live_store,
                live_date,
                live_total,
                live_transaction_id,
                live_source_type,
            ) = live_receipt

            print()
            print("Live receipt:")
            print(
                f"- id={live_id}"
                f" | date={live_date}"
                f" | store={live_store}"
                f" | total={live_total}"
                f" | transaction_id={live_transaction_id}"
                f" | source_type={live_source_type}"
            )

            cur.execute(
                """
                SELECT
                    id,
                    total,
                    warehouse_number,
                    register_number,
                    historical_transaction_number,
                    transaction_time,
                    transaction_id
                FROM receipts
                WHERE source_type = 'costco_shopping_history'
                  AND purchase_date = %s
                ORDER BY id;
                """,
                (live_date,),
            )

            historical_receipts = cur.fetchall()

            print()
            print(
                f"Historical transactions on {live_date}: "
                f"{len(historical_receipts)}"
            )

            for row in historical_receipts:
                (
                    receipt_id,
                    total,
                    warehouse,
                    register,
                    transaction_number,
                    transaction_time,
                    transaction_id,
                ) = row

                marker = (
                    " <-- SAME TOTAL"
                    if total == live_total
                    else ""
                )

                print(
                    f"- id={receipt_id}"
                    f" | total={total}"
                    f" | warehouse={warehouse}"
                    f" | register={register}"
                    f" | tran={transaction_number}"
                    f" | time={transaction_time}"
                    f"{marker}"
                )

            print()
            print("Live receipt items:")
            print("-------------------")

            cur.execute(
                """
                SELECT
                    store_item_code,
                    raw_description,
                    quantity,
                    total_price
                FROM receipt_items
                WHERE receipt_id = %s
                ORDER BY id;
                """,
                (LIVE_RECEIPT_ID,),
            )

            for (
                item_code,
                description,
                quantity,
                total_price,
            ) in cur.fetchall():
                print(
                    f"- code={item_code}"
                    f" | {description}"
                    f" | qty={quantity}"
                    f" | total={total_price}"
                )

            for historical_row in historical_receipts:
                historical_id = historical_row[0]

                print()
                print(
                    f"Historical receipt "
                    f"id={historical_id} items:"
                )
                print("-------------------------------")

                cur.execute(
                    """
                    SELECT
                        store_item_code,
                        raw_description,
                        quantity,
                        total_price,
                        historical_row_type
                    FROM receipt_items
                    WHERE receipt_id = %s
                    ORDER BY source_row_number, id;
                    """,
                    (historical_id,),
                )

                for (
                    item_code,
                    description,
                    quantity,
                    total_price,
                    row_type,
                ) in cur.fetchall():
                    print(
                        f"- code={item_code}"
                        f" | {description}"
                        f" | qty={quantity}"
                        f" | total={total_price}"
                        f" | type={row_type}"
                    )

                cur.execute(
                    """
                    SELECT
                        related_item_code,
                        raw_description,
                        amount,
                        historical_row_type
                    FROM receipt_discounts
                    WHERE receipt_id = %s
                    ORDER BY source_row_number, id;
                    """,
                    (historical_id,),
                )

                discounts = cur.fetchall()

                if discounts:
                    print("  Discounts:")

                    for (
                        related_item_code,
                        description,
                        amount,
                        row_type,
                    ) in discounts:
                        print(
                            f"  - related={related_item_code}"
                            f" | {description}"
                            f" | amount={amount}"
                            f" | type={row_type}"
                        )


if __name__ == "__main__":
    main()