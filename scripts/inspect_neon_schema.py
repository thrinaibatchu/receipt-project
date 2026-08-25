import os

import psycopg
from dotenv import load_dotenv


def main():
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )

            tables = [row[0] for row in cursor.fetchall()]

    print("Neon tables:")

    for table in tables:
        print(f"- {table}")


if __name__ == "__main__":
    main()
