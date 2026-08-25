import os

import psycopg
from dotenv import load_dotenv


def main():
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from .env")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    current_database(),
                    current_user,
                    version()
                """
            )

            database, user, version = cursor.fetchone()

    print("Neon PostgreSQL connection: SUCCESS")
    print(f"Database: {database}")
    print(f"User returned: {'YES' if user else 'NO'}")
    print(
        "PostgreSQL server returned:",
        "YES" if version else "NO",
    )


if __name__ == "__main__":
    main()
