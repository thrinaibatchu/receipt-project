import os

import psycopg
from dotenv import load_dotenv
from psycopg.errors import InsufficientPrivilege


def get_analytics_database_url() -> str:
    load_dotenv()

    database_url = os.getenv("ANALYTICS_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "ANALYTICS_DATABASE_URL is missing"
        )

    return database_url


def main() -> None:
    with psycopg.connect(
        get_analytics_database_url()
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM receipts
                """
            )

            receipt_count = cursor.fetchone()[0]

            print(
                "Read-only SELECT: SUCCESS"
            )
            print(
                f"Receipt count: {receipt_count}"
            )

            try:
                cursor.execute(
                    """
                    INSERT INTO products (
                        canonical_name
                    )
                    VALUES (
                        '_READ_ONLY_PERMISSION_TEST_'
                    )
                    """
                )

            except InsufficientPrivilege:
                connection.rollback()

                print(
                    "Read-only INSERT rejection: SUCCESS"
                )

            else:
                connection.rollback()

                raise RuntimeError(
                    "Read-only credential unexpectedly "
                    "allowed INSERT."
                )


if __name__ == "__main__":
    main()