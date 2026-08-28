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
            print("Historical key verification")
            print("---------------------------")

            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'receipts'
                      AND column_name = 'historical_key'
                );
                """
            )

            column_exists = cur.fetchone()[0]

            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename = 'receipts'
                      AND indexname = 'receipts_historical_key_uidx'
                );
                """
            )

            index_exists = cur.fetchone()[0]

            cur.execute(
                """
                SELECT
                    COUNT(*),
                    COUNT(historical_key)
                FROM receipts;
                """
            )

            (
                receipt_count,
                historical_key_count,
            ) = cur.fetchone()

            cur.execute(
                """
                SELECT
                    source_type,
                    COUNT(*)
                FROM receipts
                GROUP BY source_type
                ORDER BY source_type;
                """
            )

            source_counts = cur.fetchall()

            print(
                f"historical_key column: "
                f"{'PASS' if column_exists else 'FAIL'}"
            )

            print(
                f"unique partial index: "
                f"{'PASS' if index_exists else 'FAIL'}"
            )

            print(
                f"Receipt count: {receipt_count}"
            )

            print(
                "Receipts with historical_key: "
                f"{historical_key_count}"
            )

            print()
            print("Receipts by source type:")

            for source_type, count in source_counts:
                print(
                    f"- {source_type}: {count}"
                )

            if not column_exists:
                raise RuntimeError(
                    "historical_key column is missing."
                )

            if not index_exists:
                raise RuntimeError(
                    "Historical key unique index is missing."
                )

            if historical_key_count != 0:
                raise RuntimeError(
                    "Existing live receipts unexpectedly "
                    "contain historical keys."
                )

            print()
            print(
                "Historical key verification: PASS"
            )


if __name__ == "__main__":
    main()