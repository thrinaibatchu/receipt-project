from __future__ import annotations

import os

import psycopg
from dotenv import load_dotenv


EXPECTED_COLUMNS = {
    "receipts": {
        "source_type",
        "warehouse_number",
        "register_number",
        "historical_transaction_number",
        "transaction_time",
    },
    "receipt_items": {
        "source_row_number",
        "historical_row_type",
    },
    "receipt_discounts": {
        "source_row_number",
        "historical_row_type",
    },
}


def get_columns(
    cur: psycopg.Cursor,
    table_name: str,
) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position;
        """,
        (table_name,),
    )

    return {
        row[0]
        for row in cur.fetchall()
    }


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
            print("Historical schema verification")
            print("------------------------------")

            schema_ok = True

            for (
                table_name,
                expected_columns,
            ) in EXPECTED_COLUMNS.items():
                actual_columns = get_columns(
                    cur,
                    table_name,
                )

                missing = (
                    expected_columns
                    - actual_columns
                )

                if missing:
                    schema_ok = False

                    print(
                        f"{table_name}: FAIL"
                    )

                    print(
                        "  Missing columns: "
                        + ", ".join(
                            sorted(missing)
                        )
                    )

                else:
                    print(
                        f"{table_name}: PASS"
                    )

            cur.execute(
                """
                SELECT COUNT(*)
                FROM receipts;
                """
            )

            receipt_count = (
                cur.fetchone()[0]
            )

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

            source_type_counts = (
                cur.fetchall()
            )

            cur.execute(
                """
                SELECT
                    id,
                    purchase_date,
                    store_name,
                    total,
                    source_type
                FROM receipts
                ORDER BY id;
                """
            )

            receipts = (
                cur.fetchall()
            )

            print()
            print(
                f"Receipt count: "
                f"{receipt_count}"
            )

            print()
            print(
                "Receipts by source type:"
            )

            for (
                source_type,
                count,
            ) in source_type_counts:
                print(
                    f"- {source_type}: "
                    f"{count}"
                )

            print()
            print(
                "Current receipts:"
            )

            for (
                receipt_id,
                purchase_date,
                store_name,
                total,
                source_type,
            ) in receipts:
                print(
                    f"- id={receipt_id} | "
                    f"{purchase_date} | "
                    f"{store_name} | "
                    f"total={total} | "
                    f"source_type="
                    f"{source_type}"
                )

            print()

            if not schema_ok:
                raise RuntimeError(
                    "Historical schema "
                    "verification failed."
                )

            print(
                "Schema verification: PASS"
            )


if __name__ == "__main__":
    main()