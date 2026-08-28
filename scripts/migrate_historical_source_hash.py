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
            print("Preparing source_hash for historical imports")
            print("--------------------------------------------")

            cur.execute(
                """
                ALTER TABLE receipts
                ALTER COLUMN source_hash DROP NOT NULL;
                """
            )

        conn.commit()

    print(
        "source_hash nullability migration "
        "committed successfully."
    )


if __name__ == "__main__":
    main()