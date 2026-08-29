from __future__ import annotations

from collections import defaultdict

import psycopg

from receipt_project.analytics.product_matching import (
    build_description_code_index,
    infer_item_code_from_exact_description,
    normalize_store_identity,
    normalize_store_item_code,
)
from receipt_project.analytics.queries import (
    get_database_url,
)


def get_purchase_item_rows() -> list[dict]:
    sql = """
        SELECT
            ri.id,
            ri.receipt_id,
            r.store_name,
            ri.store_item_code,
            ri.raw_description,
            ri.product_id
        FROM receipt_items ri
        JOIN receipts r
          ON r.id = ri.receipt_id
        WHERE r.total > 0
          AND ri.quantity > 0
        ORDER BY
            r.store_name,
            ri.store_item_code,
            ri.raw_description,
            ri.id
    """

    with psycopg.connect(
        get_database_url()
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)

            return [
                {
                    "receipt_item_id": row[0],
                    "receipt_id": row[1],
                    "store_name": row[2],
                    "store_item_code": row[3],
                    "raw_description": row[4],
                    "product_id": row[5],
                }
                for row in cursor.fetchall()
            ]


def build_identity_assignments(
    rows: list[dict],
) -> tuple[
    dict[
        tuple[str, str],
        list[dict],
    ],
    list[dict],
]:
    description_rows = [
        (
            row["store_name"],
            row["store_item_code"],
            row["raw_description"],
        )
        for row in rows
    ]

    description_code_index = (
        build_description_code_index(
            description_rows
        )
    )

    assignments: dict[
        tuple[str, str],
        list[dict],
    ] = defaultdict(list)

    unresolved: list[dict] = []

    for row in rows:
        normalized_store = (
            normalize_store_identity(
                row["store_name"]
            )
        )

        normalized_code = (
            normalize_store_item_code(
                row["store_item_code"]
            )
        )

        identity_source = (
            "actual_item_code"
        )

        if normalized_code is None:
            normalized_code = (
                infer_item_code_from_exact_description(
                    row["store_name"],
                    row["raw_description"],
                    description_code_index,
                )
            )

            if normalized_code is None:
                unresolved.append(
                    row
                )
                continue

            identity_source = (
                "exact_description_bridge"
            )

        identity_key = (
            normalized_store,
            normalized_code,
        )

        assignment = dict(row)

        assignment[
            "identity_source"
        ] = identity_source

        assignments[
            identity_key
        ].append(
            assignment
        )

    return (
        dict(assignments),
        unresolved,
    )


def print_summary(
    assignments: dict[
        tuple[str, str],
        list[dict],
    ],
    unresolved: list[dict],
) -> None:
    assigned_rows = sum(
        len(rows)
        for rows in assignments.values()
    )

    existing_product_ids = sum(
        1
        for rows in assignments.values()
        for row in rows
        if row["product_id"] is not None
    )

    bridged_rows = sum(
        1
        for rows in assignments.values()
        for row in rows
        if (
            row["identity_source"]
            == "exact_description_bridge"
        )
    )

    print()
    print("=" * 70)
    print(
        "PRODUCT PERSISTENCE PREVIEW"
    )
    print("=" * 70)

    print(
        f"Deterministic product identities: "
        f"{len(assignments)}"
    )

    print(
        f"Receipt-item rows assignable: "
        f"{assigned_rows}"
    )

    print(
        f"Rows using exact-description bridge: "
        f"{bridged_rows}"
    )

    print(
        f"Unresolved receipt-item rows: "
        f"{len(unresolved)}"
    )

    print(
        f"Rows already carrying product_id: "
        f"{existing_product_ids}"
    )


def print_focus_identity(
    assignments: dict[
        tuple[str, str],
        list[dict],
    ],
    store_name: str,
    store_item_code: str,
) -> None:
    identity_key = (
        normalize_store_identity(
            store_name
        ),
        normalize_store_item_code(
            store_item_code
        ),
    )

    rows = assignments.get(
        identity_key,
        [],
    )

    print()
    print("=" * 70)
    print(
        f"IDENTITY PREVIEW: "
        f"{identity_key}"
    )
    print("=" * 70)

    if not rows:
        print(
            "No matching rows."
        )
        return

    descriptions = sorted(
        {
            row["raw_description"]
            for row in rows
        }
    )

    actual_rows = sum(
        1
        for row in rows
        if (
            row["identity_source"]
            == "actual_item_code"
        )
    )

    bridged_rows = sum(
        1
        for row in rows
        if (
            row["identity_source"]
            == "exact_description_bridge"
        )
    )

    print(
        f"Receipt-item rows: "
        f"{len(rows)}"
    )

    print(
        f"Actual item-code rows: "
        f"{actual_rows}"
    )

    print(
        f"Bridged rows: "
        f"{bridged_rows}"
    )

    print(
        "Descriptions:"
    )

    for description in descriptions:
        print(
            f"  - {description}"
        )


def print_unresolved_samples(
    unresolved: list[dict],
    limit: int = 20,
) -> None:
    print()
    print("=" * 70)
    print(
        "UNRESOLVED SAMPLE"
    )
    print("=" * 70)

    if not unresolved:
        print(
            "No unresolved rows."
        )
        return

    for row in unresolved[:limit]:
        print()
        print(
            f"receipt_item_id="
            f"{row['receipt_item_id']}"
        )
        print(
            f"store="
            f"{row['store_name']!r}"
        )
        print(
            f"code="
            f"{row['store_item_code']!r}"
        )
        print(
            f"description="
            f"{row['raw_description']!r}"
        )


def main() -> None:
    rows = get_purchase_item_rows()

    assignments, unresolved = (
        build_identity_assignments(
            rows
        )
    )

    print_summary(
        assignments,
        unresolved,
    )

    print_focus_identity(
        assignments,
        "Costco Wholesale",
        "3",
    )

    print_focus_identity(
        assignments,
        "Costco Wholesale",
        "1451835",
    )

    print_unresolved_samples(
        unresolved
    )


if __name__ == "__main__":
    main()
