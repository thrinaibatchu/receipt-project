from __future__ import annotations

from receipt_project.analytics.canonical_prices import (
    get_canonical_price_history,
    get_latest_canonical_price_at_store,
    get_latest_canonical_prices_by_store,
)


def verify_whole_milk() -> None:
    history = get_canonical_price_history(
        "whole_milk"
    )

    if not history:
        raise AssertionError(
            "Whole Milk canonical price "
            "history is empty."
        )

    if not all(
        observation[
            "canonical_key"
        ] == "whole_milk"
        for observation in history
    ):
        raise AssertionError(
            "Whole Milk history contains "
            "another canonical product."
        )

    bridged = [
        observation
        for observation in history
        if (
            observation[
                "identity_source"
            ]
            == "exact_description_bridge"
        )
    ]

    if len(bridged) != 1:
        raise AssertionError(
            "Expected exactly one bridged "
            "Whole Milk observation."
        )

    latest = (
        get_latest_canonical_price_at_store(
            "whole_milk",
            "Costco",
        )
    )

    if latest is None:
        raise AssertionError(
            "Latest Whole Milk Costco "
            "price was not found."
        )

    print()
    print(
        f"Whole Milk observations: "
        f"{len(history)}"
    )

    print(
        f"Whole Milk bridged observations: "
        f"{len(bridged)}"
    )

    print(
        "Latest Whole Milk at Costco: "
        f"${latest['effective_unit_price']} "
        f"on {latest['purchase_date']}"
    )


def verify_andouille() -> None:
    history = get_canonical_price_history(
        "andouille_sausage"
    )

    if not history:
        raise AssertionError(
            "Andouille canonical price "
            "history is empty."
        )

    bridged = [
        observation
        for observation in history
        if (
            observation[
                "identity_source"
            ]
            == "exact_description_bridge"
        )
    ]

    if bridged:
        raise AssertionError(
            "Andouille should not require "
            "a bridged price observation."
        )

    latest = (
        get_latest_canonical_price_at_store(
            "andouille_sausage",
            "Costco",
        )
    )

    if latest is None:
        raise AssertionError(
            "Latest Andouille Costco "
            "price was not found."
        )

    print()
    print(
        f"Andouille observations: "
        f"{len(history)}"
    )

    print(
        "Latest Andouille at Costco: "
        f"${latest['effective_unit_price']} "
        f"on {latest['purchase_date']}"
    )


def verify_cross_store_shape() -> None:
    rows = (
        get_latest_canonical_prices_by_store(
            "whole_milk"
        )
    )

    if not rows:
        raise AssertionError(
            "Canonical cross-store result "
            "is empty."
        )

    print()
    print(
        "Whole Milk latest-price stores: "
        f"{len(rows)}"
    )

    for row in rows:
        print(
            f"  {row['store_name']}: "
            f"${row['effective_unit_price']} "
            f"on {row['purchase_date']}"
        )


def verify_unknown_product() -> None:
    try:
        get_canonical_price_history(
            "not_a_real_product"
        )
    except ValueError:
        return

    raise AssertionError(
        "Unknown canonical key must fail."
    )


def main() -> None:
    verify_whole_milk()
    verify_andouille()
    verify_cross_store_shape()
    verify_unknown_product()

    print()
    print(
        "Canonical price analytics tests "
        "passed."
    )


if __name__ == "__main__":
    main()
