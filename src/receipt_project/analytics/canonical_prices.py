from __future__ import annotations

from datetime import date

import psycopg

from receipt_project.analytics.canonical_products import (
    CANONICAL_PRODUCTS,
    STORE_PRODUCT_LINKS,
)
from receipt_project.analytics.item_prices import (
    ITEM_PRICE_CTE,
    row_to_observation,
)
from receipt_project.analytics.product_matching import (
    build_description_code_index,
    infer_item_code_from_exact_description,
    normalize_store_identity,
    normalize_store_item_code,
)
from receipt_project.analytics.queries import (
    get_database_url,
)


def get_canonical_store_links(
    canonical_key: str,
):
    if canonical_key not in CANONICAL_PRODUCTS:
        raise ValueError(
            "Unknown canonical product "
            f"{canonical_key!r}."
        )

    return [
        link
        for link in STORE_PRODUCT_LINKS
        if link.canonical_key
        == canonical_key
    ]


def get_store_description_rows(
    normalized_store_name: str,
) -> list[
    tuple[str, str | None, str]
]:
    """
    Return raw purchase-item identity evidence for one store.

    This query intentionally does not calculate prices.
    It is used only to determine whether missing item codes
    can use the already-verified exact-description bridge.
    """
    sql = """
        SELECT DISTINCT
            r.store_name,
            ri.store_item_code,
            ri.raw_description
        FROM receipt_items ri
        JOIN receipts r
          ON r.id = ri.receipt_id
        WHERE r.total > 0
          AND ri.quantity > 0
          AND UPPER(TRIM(r.store_name)) = %s
        ORDER BY
            ri.store_item_code,
            ri.raw_description
    """

    with psycopg.connect(
        get_database_url()
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                (normalized_store_name,),
            )

            return cursor.fetchall()


def get_bridge_descriptions(
    normalized_store_name: str,
    store_item_code: str,
) -> set[str]:
    """
    Find missing-code descriptions that deterministically bridge
    to one specific store item code.

    No fuzzy matching is performed.
    """
    rows = get_store_description_rows(
        normalized_store_name
    )

    description_code_index = (
        build_description_code_index(
            rows
        )
    )

    bridge_descriptions: set[str] = set()

    for (
        store_name,
        observed_code,
        raw_description,
    ) in rows:
        if (
            normalize_store_item_code(
                observed_code
            )
            is not None
        ):
            continue

        inferred_code = (
            infer_item_code_from_exact_description(
                store_name,
                raw_description,
                description_code_index,
            )
        )

        if inferred_code == store_item_code:
            bridge_descriptions.add(
                raw_description
            )

    return bridge_descriptions


def get_identity_price_observations(
    store_name: str,
    store_item_code: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    """
    Return effective-price observations for one verified
    store-product identity.

    Actual item-code observations are selected directly.

    Missing-code observations are included only when their
    descriptions deterministically bridge to this exact item
    code at the same store.
    """
    normalized_store = (
        normalize_store_identity(
            store_name
        )
    )

    normalized_code = (
        normalize_store_item_code(
            store_item_code
        )
    )

    if normalized_code is None:
        raise ValueError(
            "Store-product identity requires "
            "an item code."
        )

    bridge_descriptions = (
        get_bridge_descriptions(
            normalized_store,
            normalized_code,
        )
    )

    sql = (
        ITEM_PRICE_CTE
        + """
        SELECT
            receipt_id,
            purchase_date,
            store_name,
            source_type,
            store_item_code,
            raw_description,
            quantity,
            gross_line_price,
            item_discount,
            effective_line_price,
            effective_unit_price
        FROM item_prices
        WHERE UPPER(TRIM(store_name)) = %s
          AND (
              store_item_code = %s
              OR (
                  store_item_code IS NULL
                  AND raw_description = ANY(%s)
              )
          )
          AND (
              %s::date IS NULL
              OR purchase_date >= %s::date
          )
          AND (
              %s::date IS NULL
              OR purchase_date <= %s::date
          )
        ORDER BY
            purchase_date,
            receipt_id,
            store_item_code
        """
    )

    bridge_list = sorted(
        bridge_descriptions
    )

    with psycopg.connect(
        get_database_url()
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                (
                    normalized_store,
                    normalized_code,
                    bridge_list,
                    start_date,
                    start_date,
                    end_date,
                    end_date,
                ),
            )

            rows = cursor.fetchall()

    observations: list[dict] = []

    for row in rows:
        observation = (
            row_to_observation(
                row
            )
        )

        actual_code = (
            normalize_store_item_code(
                observation[
                    "store_item_code"
                ]
            )
        )

        if actual_code is None:
            identity_source = (
                "exact_description_bridge"
            )
        else:
            identity_source = (
                "actual_item_code"
            )

        observation[
            "resolved_store_item_code"
        ] = normalized_code

        observation[
            "identity_source"
        ] = identity_source

        observations.append(
            observation
        )

    return observations


def get_canonical_price_history(
    canonical_key: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    """
    Return effective price observations for all explicitly
    registered store identities belonging to one canonical
    product.

    No fuzzy matching or LLM inference is performed.
    """
    canonical_product = (
        CANONICAL_PRODUCTS.get(
            canonical_key
        )
    )

    if canonical_product is None:
        raise ValueError(
            "Unknown canonical product "
            f"{canonical_key!r}."
        )

    links = get_canonical_store_links(
        canonical_key
    )

    observations: list[dict] = []

    for link in links:
        identity_observations = (
            get_identity_price_observations(
                link.store_name,
                link.store_item_code,
                start_date=start_date,
                end_date=end_date,
            )
        )

        for observation in (
            identity_observations
        ):
            observation[
                "canonical_key"
            ] = (
                canonical_product.canonical_key
            )

            observation[
                "canonical_name"
            ] = (
                canonical_product.canonical_name
            )

            observation[
                "canonical_match_confidence"
            ] = link.confidence

            observation[
                "canonical_match_source"
            ] = link.match_source

            observations.append(
                observation
            )

    return sorted(
        observations,
        key=lambda observation: (
            observation[
                "purchase_date"
            ],
            observation[
                "receipt_id"
            ],
        ),
    )


def get_latest_canonical_prices_by_store(
    canonical_key: str,
) -> list[dict]:
    """
    Return the latest effective observation for each store
    currently linked to a canonical product.
    """
    observations = (
        get_canonical_price_history(
            canonical_key
        )
    )

    latest_by_store: dict[
        str,
        dict,
    ] = {}

    for observation in observations:
        store_name = observation[
            "store_name"
        ]

        current = latest_by_store.get(
            store_name
        )

        if current is None:
            latest_by_store[
                store_name
            ] = observation
            continue

        current_key = (
            current[
                "purchase_date"
            ],
            current[
                "receipt_id"
            ],
        )

        new_key = (
            observation[
                "purchase_date"
            ],
            observation[
                "receipt_id"
            ],
        )

        if new_key > current_key:
            latest_by_store[
                store_name
            ] = observation

    return [
        latest_by_store[
            store_name
        ]
        for store_name in sorted(
            latest_by_store
        )
    ]


def get_latest_canonical_price_at_store(
    canonical_key: str,
    store_name: str,
) -> dict | None:
    observations = (
        get_latest_canonical_prices_by_store(
            canonical_key
        )
    )

    requested_store = (
        store_name.strip().lower()
    )

    for observation in observations:
        normalized_store = (
            observation[
                "store_name"
            ].strip().lower()
        )

        if (
            requested_store
            in normalized_store
        ):
            return observation

    return None
