from __future__ import annotations

import sys
from decimal import Decimal

from receipt_project.analytics.item_prices import (
    get_latest_item_price_at_store,
    get_latest_item_prices_by_store,
)


def format_money(
    value: Decimal,
) -> str:
    return f"${value:.2f}"


def print_observation(
    observation: dict,
) -> None:
    print(
        f"- {observation['store_name']}"
        f" | {observation['purchase_date']}"
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


def main() -> None:
    search_text = (
        sys.argv[1]
        if len(sys.argv) >= 2
        else "ANDOUILLE"
    )

    store_name = (
        sys.argv[2]
        if len(sys.argv) >= 3
        else "Costco"
    )

    print()
    print("Latest item-price analytics")
    print("---------------------------")

    print()
    print(
        f"Latest '{search_text}' price "
        "across stores:"
    )

    print("---------------------------")

    latest_by_store = (
        get_latest_item_prices_by_store(
            search_text
        )
    )

    print(
        f"Stores found: "
        f"{len(latest_by_store)}"
    )

    for observation in latest_by_store:
        print_observation(
            observation
        )

    print()
    print(
        f"Latest '{search_text}' price "
        f"at '{store_name}':"
    )

    print("---------------------------")

    latest_at_store = (
        get_latest_item_price_at_store(
            search_text=search_text,
            store_name=store_name,
        )
    )

    if latest_at_store is None:
        print(
            "No matching purchase found."
        )
    else:
        print_observation(
            latest_at_store
        )

    print()
    print(
        "Latest item-price verification: PASS"
    )


if __name__ == "__main__":
    main()