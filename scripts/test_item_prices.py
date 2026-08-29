from __future__ import annotations

import sys
from decimal import Decimal

from receipt_project.analytics.item_prices import (
    get_discounted_purchase_samples,
    get_item_price_history,
    verify_price_observation,
)


def format_money(
    value: Decimal,
) -> str:
    return f"${value:.2f}"


def main() -> None:
    search_text = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "ANDOUILLE"
    )

    print()
    print("Effective item-price analytics")
    print("------------------------------")

    print()
    print("Discounted purchase samples:")
    print("----------------------------")

    samples = (
        get_discounted_purchase_samples(
            limit=10
        )
    )

    if not samples:
        raise RuntimeError(
            "No discounted purchase samples "
            "were found."
        )

    for sample in samples:
        verify_price_observation(
            sample
        )

        print(
            f"- {sample['purchase_date']}"
            f" | {sample['store_name']}"
            f" | code="
            f"{sample['store_item_code']}"
        )

        print(
            f"  {sample['raw_description']}"
        )

        print(
            "  qty="
            f"{sample['quantity']}"
            " | gross="
            f"{format_money(sample['gross_line_price'])}"
            " | discount="
            f"{format_money(sample['item_discount'])}"
            " | effective="
            f"{format_money(sample['effective_line_price'])}"
            " | unit="
            f"{format_money(sample['effective_unit_price'])}"
        )

    print()
    print(
        f"Price history search: {search_text}"
    )
    print("----------------------------")

    history = get_item_price_history(
        search_text=search_text,
        limit=50,
    )

    print(
        f"Matching purchase observations: "
        f"{len(history)}"
    )

    for observation in history:
        verify_price_observation(
            observation
        )

        print(
            f"- {observation['purchase_date']}"
            f" | {observation['store_name']}"
            f" | code="
            f"{observation['store_item_code']}"
        )

        print(
            f"  {observation['raw_description']}"
        )

        print(
            "  qty="
            f"{observation['quantity']}"
            " | gross="
            f"{format_money(observation['gross_line_price'])}"
            " | discount="
            f"{format_money(observation['item_discount'])}"
            " | effective="
            f"{format_money(observation['effective_line_price'])}"
            " | unit="
            f"{format_money(observation['effective_unit_price'])}"
        )

    print()
    print(
        "Effective item-price verification: PASS"
    )


if __name__ == "__main__":
    main()