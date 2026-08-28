from __future__ import annotations

import sys
from collections import (
    Counter,
    defaultdict,
)
from decimal import Decimal
from pathlib import Path

from receipt_project.history.costco_statement import (
    CostcoHistoryRow,
    parse_costco_history_pdf,
)


COUPON_TYPES = {
    "coupon_discount",
    "coupon_reversal",
    "coupon_adjustment",
}


def is_effectively_blank_description(
    description: str,
) -> bool:
    cleaned = (
        description
        .replace(",", "")
        .replace(".", "")
        .strip()
    )

    return not cleaned


def format_row(
    row: CostcoHistoryRow,
) -> str:
    return (
        f"row={row.source_row_number} | "
        f"{row.purchase_date} | "
        f"WHS {row.warehouse} | "
        f"REG {row.register} | "
        f"TRN {row.transaction_number} | "
        f"item={row.item_number} | "
        f"type={row.row_type} | "
        f"qty={row.quantity} | "
        f"amount={row.amount} | "
        f"{row.description}"
    )


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: "
            "uv run python "
            "scripts/validate_costco_history.py "
            "<costco-history.pdf>"
        )

    pdf_path = Path(
        sys.argv[1]
    ).expanduser()

    result = (
        parse_costco_history_pdf(
            pdf_path
        )
    )

    rows = result.rows

    if result.failures:
        raise RuntimeError(
            "Semantic validation requires "
            "a fully parsed source. "
            f"Unparsed rows: "
            f"{len(result.failures)}"
        )

    print()
    print(
        "Costco historical "
        "semantic validation"
    )
    print(
        "-------------------------------------"
    )

    print(
        f"Parsed rows: {len(rows)}"
    )

    print(
        f"Pages: {result.page_count}"
    )

    if rows:
        dates = [
            row.purchase_date
            for row in rows
        ]

        print(
            "Date range: "
            f"{min(dates)} -> "
            f"{max(dates)}"
        )

    row_type_counts = Counter(
        row.row_type
        for row in rows
    )

    print()
    print("Row types:")

    for row_type in (
        "purchase",
        "return",
        "coupon_discount",
        "coupon_reversal",
        "coupon_adjustment",
        "adjustment",
    ):
        print(
            f"- {row_type}: "
            f"{row_type_counts[row_type]}"
        )

    # ---------------------------------------------------------
    # Purchase validation
    # ---------------------------------------------------------

    invalid_purchase_signs = [
        row
        for row in rows
        if (
            row.row_type
            == "purchase"
            and (
                row.quantity
                < Decimal("0")
                or row.amount
                < Decimal("0")
            )
        )
    ]

    print()
    print(
        "Purchase validation:"
    )

    print(
        "- negative quantity/amount "
        "violations: "
        f"{len(invalid_purchase_signs)}"
    )

    # ---------------------------------------------------------
    # Return validation
    # ---------------------------------------------------------

    invalid_returns = [
        row
        for row in rows
        if (
            row.row_type
            == "return"
            and row.amount
            >= Decimal("0")
        )
    ]

    print()
    print(
        "Return validation:"
    )

    print(
        "- return rows: "
        f"{row_type_counts['return']}"
    )

    print(
        "- invalid non-negative amount: "
        f"{len(invalid_returns)}"
    )

    # ---------------------------------------------------------
    # Group by transaction
    # ---------------------------------------------------------

    rows_by_transaction = (
        defaultdict(list)
    )

    for row in rows:
        rows_by_transaction[
            row.transaction_key
        ].append(
            row
        )

    # ---------------------------------------------------------
    # Coupon validation
    # ---------------------------------------------------------

    coupon_rows = [
        row
        for row in rows
        if row.row_type
        in COUPON_TYPES
    ]

    coupon_missing_reference = [
        row
        for row in coupon_rows
        if row.related_item_number
        is None
    ]

    coupon_without_matching_item = []

    coupon_discount_invalid_sign = []

    coupon_reversal_invalid_sign = []

    coupon_adjustment_invalid_sign = []

    coupon_reversal_without_return = []

    for coupon in coupon_rows:
        if (
            coupon.row_type
            == "coupon_discount"
            and coupon.amount
            >= Decimal("0")
        ):
            coupon_discount_invalid_sign.append(
                coupon
            )

        if (
            coupon.row_type
            == "coupon_reversal"
            and coupon.amount
            <= Decimal("0")
        ):
            coupon_reversal_invalid_sign.append(
                coupon
            )

        if (
            coupon.row_type
            == "coupon_adjustment"
            and coupon.amount
            != Decimal("0")
        ):
            coupon_adjustment_invalid_sign.append(
                coupon
            )

        if (
            coupon.related_item_number
            is None
        ):
            continue

        same_transaction_rows = (
            rows_by_transaction[
                coupon.transaction_key
            ]
        )

        matching_items = [
            row
            for row
            in same_transaction_rows
            if (
                row.item_number
                == coupon.related_item_number
                and row.row_type
                not in COUPON_TYPES
            )
        ]

        if not matching_items:
            coupon_without_matching_item.append(
                coupon
            )
            continue

        if (
            coupon.row_type
            == "coupon_reversal"
        ):
            has_return = any(
                row.row_type
                == "return"
                for row
                in matching_items
            )

            if not has_return:
                coupon_reversal_without_return.append(
                    coupon
                )

    print()
    print(
        "Coupon validation:"
    )

    print(
        "- coupon discount rows: "
        f"{row_type_counts['coupon_discount']}"
    )

    print(
        "- coupon reversal rows: "
        f"{row_type_counts['coupon_reversal']}"
    )

    print(
        "- coupon adjustment rows: "
        f"{row_type_counts['coupon_adjustment']}"
    )

    print(
        "- missing CPN item reference: "
        f"{len(coupon_missing_reference)}"
    )

    print(
        "- no matching item "
        "in same transaction: "
        f"{len(coupon_without_matching_item)}"
    )

    print(
        "- invalid discount sign: "
        f"{len(coupon_discount_invalid_sign)}"
    )

    print(
        "- invalid reversal sign: "
        f"{len(coupon_reversal_invalid_sign)}"
    )

    print(
        "- invalid adjustment sign: "
        f"{len(coupon_adjustment_invalid_sign)}"
    )

    print(
        "- reversal without "
        "matching return: "
        f"{len(coupon_reversal_without_return)}"
    )

    # ---------------------------------------------------------
    # Transaction grouping validation
    # ---------------------------------------------------------

    transaction_times = (
        defaultdict(set)
    )

    for row in rows:
        if (
            row.transaction_time
            is not None
        ):
            transaction_times[
                row.transaction_key
            ].add(
                row.transaction_time
            )

    multi_time_transactions = {
        transaction_key: times
        for (
            transaction_key,
            times,
        ) in transaction_times.items()
        if len(times) > 1
    }

    print()
    print(
        "Transaction grouping validation:"
    )

    print(
        "- distinct transaction keys: "
        f"{len(rows_by_transaction)}"
    )

    print(
        "- transaction keys with "
        "multiple transaction times: "
        f"{len(multi_time_transactions)}"
    )

    # ---------------------------------------------------------
    # Description validation
    # ---------------------------------------------------------

    suspicious_descriptions = [
        row
        for row in rows
        if (
            is_effectively_blank_description(
                row.description
            )
        )
    ]

    print()
    print(
        "Description validation:"
    )

    print(
        "- blank/effectively "
        "blank descriptions: "
        f"{len(suspicious_descriptions)}"
    )

    # ---------------------------------------------------------
    # Duplicate source rows
    # ---------------------------------------------------------

    raw_text_counts = Counter(
        (
            row.card_number,
            row.warehouse,
            row.purchase_date,
            row.raw_text,
        )
        for row in rows
    )

    duplicate_source_records = [
        (
            key,
            count,
        )
        for (
            key,
            count,
        ) in raw_text_counts.items()
        if count > 1
    ]

    duplicate_extra_rows = sum(
        count - 1
        for (
            _,
            count,
        ) in duplicate_source_records
    )

    print()
    print(
        "Duplicate validation:"
    )

    print(
        "- exact duplicated "
        "source record patterns: "
        f"{len(duplicate_source_records)}"
    )

    print(
        "- repeated rows preserved: "
        f"{duplicate_extra_rows}"
    )

    # ---------------------------------------------------------
    # Adjustment rows
    # ---------------------------------------------------------

    adjustment_rows = [
        row
        for row in rows
        if row.row_type
        == "adjustment"
    ]

    print()
    print(
        "Adjustment rows "
        f"({len(adjustment_rows)}):"
    )

    if adjustment_rows:
        for row in adjustment_rows:
            print(
                f"- {format_row(row)}"
            )
    else:
        print("- none")

    # ---------------------------------------------------------
    # Review samples
    # ---------------------------------------------------------

    review_groups = [
        (
            "Coupon reversals "
            "without matching return",
            coupon_reversal_without_return,
        ),
        (
            "Coupon adjustments",
            [
                row
                for row in coupon_rows
                if row.row_type
                == "coupon_adjustment"
            ],
        ),
        (
            "Blank descriptions",
            suspicious_descriptions,
        ),
    ]

    for (
        title,
        review_rows,
    ) in review_groups:
        if not review_rows:
            continue

        print()
        print(
            f"{title} "
            "(showing up to 20):"
        )

        for row in review_rows[:20]:
            print(
                f"- {format_row(row)}"
            )

    # ---------------------------------------------------------
    # Final assessment
    # ---------------------------------------------------------

    hard_failures = (
        len(
            invalid_purchase_signs
        )
        + len(
            invalid_returns
        )
        + len(
            coupon_missing_reference
        )
        + len(
            coupon_without_matching_item
        )
        + len(
            coupon_discount_invalid_sign
        )
        + len(
            coupon_reversal_invalid_sign
        )
        + len(
            coupon_adjustment_invalid_sign
        )
    )

    review_items = (
        len(
            coupon_reversal_without_return
        )
        + row_type_counts[
            "coupon_adjustment"
        ]
        + len(
            suspicious_descriptions
        )
        + len(
            adjustment_rows
        )
    )

    print()
    print(
        "Validation assessment:"
    )

    print(
        f"- hard failures: "
        f"{hard_failures}"
    )

    print(
        f"- review items: "
        f"{review_items}"
    )

    if hard_failures:
        print(
            "- semantic validation: FAIL"
        )

    elif review_items:
        print(
            "- semantic validation: "
            "PASS WITH REVIEW"
        )

    else:
        print(
            "- semantic validation: PASS"
        )


if __name__ == "__main__":
    main()