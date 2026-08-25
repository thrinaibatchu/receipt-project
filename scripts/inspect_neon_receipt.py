import os

import psycopg
from dotenv import load_dotenv


SOURCE_HASH = (
    "79749d2ae04953e552407cac91d2a06ca"
    "244b21afc6593f0ab1e7f266bd3a9c2"
)


def main():
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    store_name,
                    purchase_date,
                    transaction_id,
                    subtotal,
                    tax,
                    total,
                    source_file,
                    source_hash,
                    receipt_fingerprint
                FROM receipts
                WHERE source_hash = %s
                """,
                (SOURCE_HASH,),
            )

            receipt = cursor.fetchone()

            if not receipt:
                raise RuntimeError("Receipt not found in Neon")

            (
                receipt_id,
                store_name,
                purchase_date,
                transaction_id,
                subtotal,
                tax,
                total,
                source_file,
                source_hash,
                receipt_fingerprint,
            ) = receipt

            cursor.execute(
                """
                SELECT
                    store_item_code,
                    raw_description,
                    quantity,
                    unit_price,
                    total_price
                FROM receipt_items
                WHERE receipt_id = %s
                ORDER BY id
                """,
                (receipt_id,),
            )

            items = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    raw_description,
                    amount,
                    related_item_code
                FROM receipt_discounts
                WHERE receipt_id = %s
                ORDER BY id
                """,
                (receipt_id,),
            )

            discounts = cursor.fetchall()

    print("Receipt:")
    print(f"  ID: {receipt_id}")
    print(f"  Store: {store_name}")
    print(f"  Date: {purchase_date}")
    print(f"  Transaction ID: {transaction_id}")
    print(f"  Subtotal: {subtotal}")
    print(f"  Tax: {tax}")
    print(f"  Total: {total}")
    print(f"  Source file: {source_file}")
    print(f"  Source hash: {source_hash}")
    print(
        "  Receipt fingerprint:",
        receipt_fingerprint or "NULL",
    )

    print()
    print(f"Items ({len(items)}):")

    for item in items:
        print(
            f"  {item[0]} | "
            f"{item[1]} | "
            f"qty={item[2]} | "
            f"unit={item[3]} | "
            f"total={item[4]}"
        )

    print()
    print(f"Discounts ({len(discounts)}):")

    for discount in discounts:
        print(
            f"  {discount[0]} | "
            f"amount={discount[1]} | "
            f"related_item_code={discount[2]}"
        )


if __name__ == "__main__":
    main()
