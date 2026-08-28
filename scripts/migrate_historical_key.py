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
            print("Applying historical key migration")
            print("---------------------------------")

            cur.execute(
                """
                ALTER TABLE receipts
                    ADD COLUMN IF NOT EXISTS historical_key TEXT;
                """
            )

            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    receipts_historical_key_uidx
                ON receipts (historical_key)
                WHERE historical_key IS NOT NULL;
                """
            )

        conn.commit()

    print("Historical key migration committed successfully.")


if __name__ == "__main__":
    main()