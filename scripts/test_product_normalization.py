from __future__ import annotations

import psycopg

from receipt_project.analytics.product_matching import (
    ProductCandidate,
    build_product_candidates,
)
from receipt_project.analytics.queries import (
    get_database_url,
)


SEARCH_TERMS = (
    "milk",
    "andouille",
)


def get_matching_descriptions(
    search_text: str,
) -> list[
    tuple[str, str | None, str]
]:
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
          AND ri.raw_description ILIKE %s
        ORDER BY
            r.store_name,
            ri.store_item_code,
            ri.raw_description
    """

    pattern = f"%{search_text}%"

    with psycopg.connect(
        get_database_url()
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                (pattern,),
            )

            return cursor.fetchall()


def verify_candidate_helpers() -> None:
    sample_rows = [
        (
            "Costco Wholesale",
            "3",
            "KS WHOLE MILK 1 GALLON",
        ),
        (
            "COSTCO WHOLESALE",
            "3",
            "WHOLE MILK",
        ),
        (
            "Costco Wholesale",
            None,
            "WHOLE MILK",
        ),
    ]

    candidates = build_product_candidates(
        sample_rows
    )

    if len(candidates) != 1:
        raise AssertionError(
            "Expected exactly one "
            "Whole Milk candidate."
        )

    candidate = candidates[0]

    if not isinstance(
        candidate,
        ProductCandidate,
    ):
        raise AssertionError(
            "Expected ProductCandidate."
        )

    if candidate.store_name != (
        "COSTCO WHOLESALE"
    ):
        raise AssertionError(
            "Unexpected normalized store."
        )

    if candidate.store_item_code != "3":
        raise AssertionError(
            "Expected item code '3'."
        )

    if candidate.actual_item_code_rows != 2:
        raise AssertionError(
            "Expected two actual-code rows."
        )

    if candidate.bridged_rows != 1:
        raise AssertionError(
            "Expected one bridged row."
        )

    if candidate.confidence != "high":
        raise AssertionError(
            "Expected high confidence."
        )

    print(
        "Product candidate helper "
        "tests passed."
    )


def print_candidate_report(
    search_text: str,
) -> None:
    rows = get_matching_descriptions(
        search_text
    )

    candidates = build_product_candidates(
        rows
    )

    print()
    print("=" * 70)
    print(
        f"PRODUCT CANDIDATES: "
        f"{search_text}"
    )
    print("=" * 70)

    print(
        f"Candidates: {len(candidates)}"
    )

    for candidate in candidates:
        print()
        print(
            f"STORE: "
            f"{candidate.store_name}"
        )

        print(
            f"ITEM CODE: "
            f"{candidate.store_item_code}"
        )

        print(
            f"CONFIDENCE: "
            f"{candidate.confidence}"
        )

        print(
            f"ACTUAL-CODE ROWS: "
            f"{candidate.actual_item_code_rows}"
        )

        print(
            f"BRIDGED ROWS: "
            f"{candidate.bridged_rows}"
        )

        print(
            "RAW DESCRIPTIONS:"
        )

        for description in (
            candidate.raw_descriptions
        ):
            print(
                f"  - {description}"
            )

        print(
            "NORMALIZED DESCRIPTIONS:"
        )

        for description in (
            candidate.normalized_descriptions
        ):
            print(
                f"  - {description}"
            )


def main() -> None:
    verify_candidate_helpers()

    for search_text in SEARCH_TERMS:
        print_candidate_report(
            search_text
        )


if __name__ == "__main__":
    main()
