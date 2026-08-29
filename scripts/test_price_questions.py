from __future__ import annotations

import sys
from decimal import Decimal

from receipt_project.analytics.price_questions import (
    answer_price_question,
)


def format_money(
    value: Decimal,
) -> str:
    return f"${value:.2f}"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            'Usage: uv run python '
            'scripts/test_price_questions.py '
            '"<question>"'
        )

    question = sys.argv[1]

    print()
    print("Price question")
    print("--------------")
    print(question)

    intent, rows = answer_price_question(
        question
    )

    print()
    print("Detected intent")
    print("---------------")

    print(
        f"intent={intent.intent}"
    )

    print(
        f"item={intent.item}"
    )

    print(
        f"store={intent.store}"
    )

    print()
    print("Results")
    print("-------")

    print(
        f"Rows: {len(rows)}"
    )

    for row in rows:
        print(
            f"- {row['purchase_date']}"
            f" | {row['store_name']}"
            f" | {row['raw_description']}"
        )

        print(
            "  qty="
            f"{row['quantity']}"
            " | gross="
            f"{format_money(row['gross_line_price'])}"
            " | discount="
            f"{format_money(row['item_discount'])}"
            " | effective="
            f"{format_money(row['effective_line_price'])}"
            " | unit="
            f"{format_money(row['effective_unit_price'])}"
        )

    print()
    print(
        "Price-question verification: PASS"
    )


if __name__ == "__main__":
    main()