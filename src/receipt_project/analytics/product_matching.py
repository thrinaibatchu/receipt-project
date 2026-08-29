from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass


ProductRow = tuple[
    str,
    str | None,
    str,
]


@dataclass(frozen=True)
class ProductCandidate:
    store_name: str
    store_item_code: str
    raw_descriptions: tuple[str, ...]
    normalized_descriptions: tuple[str, ...]
    actual_item_code_rows: int
    bridged_rows: int
    confidence: str


def normalize_product_description(
    description: str,
) -> str:
    """
    Normalize raw receipt text conservatively.

    This function does not attempt semantic product matching
    or canonical naming.
    """
    normalized = description.strip().lower()

    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def normalize_store_identity(
    store_name: str,
) -> str:
    return " ".join(
        store_name.strip().upper().split()
    )


def normalize_store_item_code(
    store_item_code: str | None,
) -> str | None:
    if store_item_code is None:
        return None

    normalized = store_item_code.strip()

    if not normalized:
        return None

    return normalized.upper()


def get_same_store_item_key(
    store_name: str,
    store_item_code: str | None,
) -> tuple[str, str] | None:
    normalized_code = (
        normalize_store_item_code(
            store_item_code
        )
    )

    if normalized_code is None:
        return None

    return (
        normalize_store_identity(
            store_name
        ),
        normalized_code,
    )


def build_description_code_index(
    rows: list[ProductRow],
) -> dict[
    tuple[str, str],
    set[str],
]:
    index: dict[
        tuple[str, str],
        set[str],
    ] = defaultdict(set)

    for (
        store_name,
        store_item_code,
        raw_description,
    ) in rows:
        normalized_code = (
            normalize_store_item_code(
                store_item_code
            )
        )

        if normalized_code is None:
            continue

        key = (
            normalize_store_identity(
                store_name
            ),
            normalize_product_description(
                raw_description
            ),
        )

        index[key].add(
            normalized_code
        )

    return dict(index)


def infer_item_code_from_exact_description(
    store_name: str,
    raw_description: str,
    description_code_index: dict[
        tuple[str, str],
        set[str],
    ],
) -> str | None:
    key = (
        normalize_store_identity(
            store_name
        ),
        normalize_product_description(
            raw_description
        ),
    )

    candidate_codes = (
        description_code_index.get(
            key,
            set(),
        )
    )

    if len(candidate_codes) != 1:
        return None

    return next(
        iter(candidate_codes)
    )


def build_deterministic_product_clusters(
    rows: list[ProductRow],
) -> dict[
    tuple[str, str],
    dict,
]:
    description_code_index = (
        build_description_code_index(
            rows
        )
    )

    clusters: dict[
        tuple[str, str],
        dict,
    ] = {}

    for (
        store_name,
        store_item_code,
        raw_description,
    ) in rows:
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

        identity_source = (
            "actual_item_code"
        )

        if normalized_code is None:
            normalized_code = (
                infer_item_code_from_exact_description(
                    store_name,
                    raw_description,
                    description_code_index,
                )
            )

            if normalized_code is None:
                continue

            identity_source = (
                "exact_description_bridge"
            )

        identity_key = (
            normalized_store,
            normalized_code,
        )

        if identity_key not in clusters:
            clusters[identity_key] = {
                "store_name":
                    normalized_store,
                "store_item_code":
                    normalized_code,
                "raw_descriptions":
                    set(),
                "normalized_descriptions":
                    set(),
                "actual_item_code_rows":
                    0,
                "bridged_rows":
                    0,
            }

        cluster = clusters[
            identity_key
        ]

        cluster[
            "raw_descriptions"
        ].add(
            raw_description
        )

        cluster[
            "normalized_descriptions"
        ].add(
            normalize_product_description(
                raw_description
            )
        )

        if (
            identity_source
            == "actual_item_code"
        ):
            cluster[
                "actual_item_code_rows"
            ] += 1
        else:
            cluster[
                "bridged_rows"
            ] += 1

    return clusters


def build_product_candidates(
    rows: list[ProductRow],
) -> list[ProductCandidate]:
    """
    Convert deterministic clusters into read-only product
    candidates.

    These candidates are NOT database products yet.

    No canonical_name is generated here because product naming
    and semantic cross-store identity have not been verified.
    """
    clusters = (
        build_deterministic_product_clusters(
            rows
        )
    )

    candidates: list[
        ProductCandidate
    ] = []

    for identity_key in sorted(
        clusters
    ):
        cluster = clusters[
            identity_key
        ]

        candidate = ProductCandidate(
            store_name=cluster[
                "store_name"
            ],
            store_item_code=cluster[
                "store_item_code"
            ],
            raw_descriptions=tuple(
                sorted(
                    cluster[
                        "raw_descriptions"
                    ]
                )
            ),
            normalized_descriptions=tuple(
                sorted(
                    cluster[
                        "normalized_descriptions"
                    ]
                )
            ),
            actual_item_code_rows=cluster[
                "actual_item_code_rows"
            ],
            bridged_rows=cluster[
                "bridged_rows"
            ],
            confidence="high",
        )

        candidates.append(
            candidate
        )

    return candidates
