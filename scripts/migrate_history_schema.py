from __future__ import annotations

import os

import psycopg
from dotenv import load_dotenv


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
            print("Applying historical import schema migration")
            print("-------------------------------------------")

            cur.execute(
                """
                ALTER TABLE receipts
                    ADD COLUMN IF NOT EXISTS source_type TEXT,
                    ADD COLUMN IF NOT EXISTS warehouse_number TEXT,
                    ADD COLUMN IF NOT EXISTS register_number TEXT,
                    ADD COLUMN IF NOT EXISTS historical_transaction_number TEXT,
                    ADD COLUMN IF NOT EXISTS transaction_time TEXT;
                """
            )

            cur.execute(
                """
                ALTER TABLE receipt_items
                    ADD COLUMN IF NOT EXISTS source_row_number INTEGER,
                    ADD COLUMN IF NOT EXISTS historical_row_type TEXT;
                """
            )

            cur.execute(
                """
                ALTER TABLE receipt_discounts
                    ADD COLUMN IF NOT EXISTS source_row_number INTEGER,
                    ADD COLUMN IF NOT EXISTS historical_row_type TEXT;
                """
            )

            cur.execute(
                """
                UPDATE receipts
                SET source_type = 'live_receipt'
                WHERE source_type IS NULL;
                """
            )

        conn.commit()

    print("Migration committed successfully.")


if __name__ == "__main__":
    main()