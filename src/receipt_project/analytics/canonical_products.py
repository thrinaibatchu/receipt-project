from __future__ import annotations

from dataclasses import dataclass

from receipt_project.analytics.product_matching import (
    normalize_store_identity,
    normalize_store_item_code,
)


@dataclass(frozen=True)
class CanonicalProduct:
    canonical_key: str
    canonical_name: str
    category: str | None = None


@dataclass(frozen=True)
class StoreProductLink:
    store_name: str
    store_item_code: str
    canonical_key: str
    confidence: str
    match_source: str


CANONICAL_PRODUCTS = {
    "whole_milk": CanonicalProduct(
        canonical_key="whole_milk",
        canonical_name="Whole Milk",
        category="Dairy",
    ),
    "andouille_sausage": CanonicalProduct(
        canonical_key="andouille_sausage",
        canonical_name="Andouille Sausage",
        category="Meat",
    ),
}


STORE_PRODUCT_LINKS = (
    StoreProductLink(
        store_name="COSTCO WHOLESALE",
        store_item_code="3",
        canonical_key="whole_milk",
        confidence="high",
        match_source="verified_manual_seed",
    ),
    StoreProductLink(
        store_name="COSTCO WHOLESALE",
        store_item_code="1451835",
        canonical_key="andouille_sausage",
        confidence="high",
        match_source="verified_manual_seed",
    ),
)


def build_store_product_link_index(
) -> dict[
    tuple[str, str],
    StoreProductLink,
]:
    index: dict[
        tuple[str, str],
        StoreProductLink,
    ] = {}

    for link in STORE_PRODUCT_LINKS:
        normalized_store = (
            normalize_store_identity(
                link.store_name
            )
        )

        normalized_code = (
            normalize_store_item_code(
                link.store_item_code
            )
        )

        if normalized_code is None:
            raise RuntimeError(
                "Canonical store-product link "
                "cannot have a missing item code."
            )

        identity_key = (
            normalized_store,
            normalized_code,
        )

        if identity_key in index:
            raise RuntimeError(
                "Duplicate canonical mapping for "
                f"{identity_key!r}."
            )

        if (
            link.canonical_key
            not in CANONICAL_PRODUCTS
        ):
            raise RuntimeError(
                "Store-product link references "
                "unknown canonical product "
                f"{link.canonical_key!r}."
            )

        index[
            identity_key
        ] = link

    return index


STORE_PRODUCT_LINK_INDEX = (
    build_store_product_link_index()
)


def resolve_canonical_product(
    store_name: str,
    store_item_code: str | None,
) -> CanonicalProduct | None:
    """
    Resolve a verified same-store product identity to a
    canonical product.

    This function deliberately performs no fuzzy matching,
    description matching, or LLM inference.
    """
    normalized_code = (
        normalize_store_item_code(
            store_item_code
        )
    )

    if normalized_code is None:
        return None

    identity_key = (
        normalize_store_identity(
            store_name
        ),
        normalized_code,
    )

    link = STORE_PRODUCT_LINK_INDEX.get(
        identity_key
    )

    if link is None:
        return None

    return CANONICAL_PRODUCTS[
        link.canonical_key
    ]


def get_store_product_link(
    store_name: str,
    store_item_code: str | None,
) -> StoreProductLink | None:
    normalized_code = (
        normalize_store_item_code(
            store_item_code
        )
    )

    if normalized_code is None:
        return None

    identity_key = (
        normalize_store_identity(
            store_name
        ),
        normalized_code,
    )

    return STORE_PRODUCT_LINK_INDEX.get(
        identity_key
    )
