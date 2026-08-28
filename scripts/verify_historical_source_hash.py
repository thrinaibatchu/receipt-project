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
            print("Historical source_hash verification")
            print("-----------------------------------")

            cur.execute(
                """
                SELECT
                    is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'receipts'
                  AND column_name = 'source_hash';
                """
            )

            row = cur.fetchone()

            if row is None:
                raise RuntimeError(
                    "receipts.source_hash column "
                    "was not found."
                )

            is_nullable = row[0]

            cur.execute(
                """
                SELECT
                    COUNT(*)
                FROM receipts;
                """
            )

            receipt_count = cur.fetchone()[0]

            cur.execute(
                """
                SELECT
                    COUNT(*)
                FROM receipts
                WHERE source_type = 'live_receipt'
                  AND source_hash IS NULL;
                """
            )

            live_receipts_missing_hash = (
                cur.fetchone()[0]
            )

            cur.execute(
                """
                SELECT
                    id,
                    source_type,
                    source_hash IS NOT NULL
                        AS has_source_hash,
                    historical_key
                FROM receipts
                ORDER BY id;
                """
            )

            receipts = cur.fetchall()

            print(
                "source_hash nullable: "
                f"{'PASS' if is_nullable == 'YES' else 'FAIL'}"
            )

            print(
                f"Receipt count: {receipt_count}"
            )

            print(
                "Live receipts missing source_hash: "
                f"{live_receipts_missing_hash}"
            )

            print()
            print("Current receipts:")

            for (
                receipt_id,
                source_type,
                has_source_hash,
                historical_key,
            ) in receipts:
                print(
                    f"- id={receipt_id} | "
                    f"source_type={source_type} | "
                    f"has_source_hash={has_source_hash} | "
                    f"historical_key="
                    f"{historical_key}"
                )

            if is_nullable != "YES":
                raise RuntimeError(
                    "source_hash is still NOT NULL."
                )

            if live_receipts_missing_hash != 0:
                raise RuntimeError(
                    "One or more existing live receipts "
                    "lost their source_hash."
                )

            print()
            print(
                "Historical source_hash "
                "verification: PASS"
            )


if __name__ == "__main__":
    main()