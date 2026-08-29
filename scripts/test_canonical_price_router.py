from __future__ import annotations

from receipt_project.analytics.canonical_products import (
    resolve_canonical_key_from_text,
)
from receipt_project.analytics.price_questions import (
    PriceQuestionIntent,
    execute_price_intent,
)


def verify_aliases() -> None:
    examples = {
        "milk": "whole_milk",
        "Whole Milk": "whole_milk",
        " whole   milk ": "whole_milk",
        "ANDOUILLE":
            "andouille_sausage",
        "Andouille Sausage":
            "andouille_sausage",
    }

    for text, expected in (
        examples.items()
    ):
        actual = (
            resolve_canonical_key_from_text(
                text
            )
        )

        if actual != expected:
            raise AssertionError(
                f"{text!r}: expected "
                f"{expected!r}, "
                f"got {actual!r}"
            )

    if (
        resolve_canonical_key_from_text(
            "okra"
        )
        is not None
    ):
        raise AssertionError(
            "Unregistered Okra must not "
            "resolve canonically."
        )

    if (
        resolve_canonical_key_from_text(
            "goat milk bar soap"
        )
        is not None
    ):
        raise AssertionError(
            "Milk Bar Soap must not "
            "resolve as Whole Milk."
        )


def verify_canonical_latest_store() -> None:
    intent = PriceQuestionIntent(
        intent="latest_at_store",
        item="milk",
        store="Costco",
    )

    rows = execute_price_intent(
        intent
    )

    if len(rows) != 1:
        raise AssertionError(
            "Expected exactly one latest "
            "Whole Milk Costco result."
        )

    row = rows[0]

    if (
        row.get("canonical_key")
        != "whole_milk"
    ):
        raise AssertionError(
            "Milk query did not use "
            "canonical pricing."
        )

    if str(
        row["effective_unit_price"]
    ) not in {
        "3.00",
        "3.0000000000000000",
    }:
        raise AssertionError(
            "Unexpected latest Whole Milk "
            "effective price."
        )

    print(
        "Canonical Milk latest-at-store "
        "routing passed."
    )

    print(
        "Latest Whole Milk at Costco: "
        f"${row['effective_unit_price']} "
        f"on {row['purchase_date']}"
    )


def verify_canonical_trend() -> None:
    intent = PriceQuestionIntent(
        intent="price_trend",
        item="Andouille",
        store=None,
    )

    rows = execute_price_intent(
        intent
    )

    if len(rows) != 39:
        raise AssertionError(
            "Expected 39 canonical "
            "Andouille observations."
        )

    if not all(
        row.get("canonical_key")
        == "andouille_sausage"
        for row in rows
    ):
        raise AssertionError(
            "Andouille trend did not use "
            "canonical pricing."
        )

    print(
        "Canonical Andouille trend "
        "routing passed."
    )


def verify_raw_fallback() -> None:
    intent = PriceQuestionIntent(
        intent="latest_at_store",
        item="Okra",
        store="Costco",
    )

    rows = execute_price_intent(
        intent
    )

    for row in rows:
        if (
            row.get("canonical_key")
            is not None
        ):
            raise AssertionError(
                "Unregistered Okra should use "
                "raw-description fallback."
            )

    print(
        "Unknown-product raw fallback "
        "routing passed."
    )


def verify_not_price_question() -> None:
    intent = PriceQuestionIntent(
        intent="not_price_question",
        item=None,
        store=None,
    )

    rows = execute_price_intent(
        intent
    )

    if rows:
        raise AssertionError(
            "Non-price question must not "
            "return price rows."
        )


def main() -> None:
    verify_aliases()
    verify_canonical_latest_store()
    verify_canonical_trend()
    verify_raw_fallback()
    verify_not_price_question()

    print()
    print(
        "Canonical-aware price router "
        "tests passed."
    )


if __name__ == "__main__":
    main()
