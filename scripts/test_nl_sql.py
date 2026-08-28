import sys

from receipt_project.analytics.nl_sql import (
    ask_receipt_database,
)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            'Usage: uv run python scripts/test_nl_sql.py '
            '"<question>"'
        )

    question = " ".join(sys.argv[1:])

    print()
    print("Question:")
    print(question)

    plan, columns, rows = ask_receipt_database(
        question
    )

    print()
    print("Generated SQL:")
    print(plan.sql)

    print()
    print("Explanation:")
    print(plan.explanation)

    print()
    print("Result columns:")
    print(columns)

    print()
    print("Source rows:")

    for row in rows:
        print(row)


if __name__ == "__main__":
    main()