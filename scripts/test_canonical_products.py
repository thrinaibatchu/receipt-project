from __future__ import annotations

from receipt_project.analytics.canonical_products import (
    CANONICAL_PRODUCTS,
    STORE_PRODUCT_LINK_INDEX,
    get_store_product_link,
    resolve_canonical_product,
)


def verify_whole_milk() -> None:
    product = resolve_canonical_product(
        "Costco Wholesale",
        "3",
    )

    if product is None:
        raise AssertionError(
            "Whole Milk canonical product "
            "was not resolved."
        )

    if product.canonical_key != "whole_milk":
        raise AssertionError(
            "Unexpected Whole Milk "
            "canonical key."
        )

    if product.canonical_name != "Whole Milk":
        raise AssertionError(
            "Unexpected Whole Milk "
            "canonical name."
        )

    link = get_store_product_link(
        "COSTCO WHOLESALE",
        "3",
    )

    if link is None:
        raise AssertionError(
            "Whole Milk store-product link "
            "was not found."
        )

    if (
        link.match_source
        != "verified_manual_seed"
    ):
        raise AssertionError(
            "Unexpected Whole Milk "
            "match source."
        )


def verify_andouille() -> None:
    product = resolve_canonical_product(
        "costco wholesale",
        "1451835",
    )

    if product is None:
        raise AssertionError(
            "Andouille canonical product "
            "was not resolved."
        )

    if (
        product.canonical_key
        != "andouille_sausage"
    ):
        raise AssertionError(
            "Unexpected Andouille "
            "canonical key."
        )

    if (
        product.canonical_name
        != "Andouille Sausage"
    ):
        raise AssertionError(
            "Unexpected Andouille "
            "canonical name."
        )


def verify_unknown_product() -> None:
    product = resolve_canonical_product(
        "Costco Wholesale",
        "1487863",
    )

    if product is not None:
        raise AssertionError(
            "Unseeded Milk Bar Soap must "
            "not resolve canonically."
        )

    product = resolve_canonical_product(
        "Costco Wholesale",
        None,
    )

    if product is not None:
        raise AssertionError(
            "Missing item code must not "
            "resolve canonically."
        )


def main() -> None:
    verify_whole_milk()
    verify_andouille()
    verify_unknown_product()

    print(
        "Canonical product registry tests "
        "passed."
    )

    print()
    print("=" * 70)
    print(
        "CANONICAL PRODUCTS"
    )
    print("=" * 70)

    for key, product in sorted(
        CANONICAL_PRODUCTS.items()
    ):
        print()
        print(
            f"KEY: {key}"
        )
        print(
            f"NAME: "
            f"{product.canonical_name}"
        )
        print(
            f"CATEGORY: "
            f"{product.category}"
        )

    print()
    print("=" * 70)
    print(
        "STORE PRODUCT LINKS"
    )
    print("=" * 70)

    for identity_key, link in sorted(
        STORE_PRODUCT_LINK_INDEX.items()
    ):
        product = (
            CANONICAL_PRODUCTS[
                link.canonical_key
            ]
        )

        print()
        print(
            f"IDENTITY: {identity_key}"
        )
        print(
            f"CANONICAL: "
            f"{product.canonical_name}"
        )
        print(
            f"CONFIDENCE: "
            f"{link.confidence}"
        )
        print(
            f"SOURCE: "
            f"{link.match_source}"
        )


if __name__ == "__main__":
    main()
