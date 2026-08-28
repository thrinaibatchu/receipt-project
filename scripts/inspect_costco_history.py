from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from receipt_project.history.costco_statement import (
    COUPON_TYPES,
    parse_costco_history_pdf,
)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: "
            "uv run python "
            "scripts/inspect_costco_history.py "
            "<costco-history.pdf>"
        )

    pdf_path = Path(
        sys.argv[1]
    ).expanduser()

    result = parse_costco_history_pdf(
        pdf_path
    )

    rows = result.rows

    print()
    print("Costco historical statement dry run")
    print("----------------------------------")

    print(
        f"Pages: {result.page_count}"
    )

    print(
        "Source records detected: "
        f"{result.source_record_count}"
    )

    print(
        f"Parsed rows: {len(rows)}"
    )

    print(
        "Unparsed rows: "
        f"{len(result.failures)}"
    )

    if rows:
        dates = [
            row.purchase_date
            for row in rows
        ]

        print(
            f"Date range: "
            f"{min(dates)} -> {max(dates)}"
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

    transaction_keys = {
        row.transaction_key
        for row in rows
    }

    print()
    print(
        "Distinct transaction keys: "
        f"{len(transaction_keys)}"
    )

    warehouse_counts = Counter(
        row.warehouse
        for row in rows
    )

    print()
    print("Top warehouses:")

    for (
        warehouse,
        count,
    ) in warehouse_counts.most_common(
        10
    ):
        print(
            f"- {warehouse}: {count} rows"
        )

    coupon_rows = [
        row
        for row in rows
        if row.row_type in COUPON_TYPES
    ]

    print()
    print("Coupon samples:")

    for row in coupon_rows[:10]:
        print(
            f"- {row.purchase_date} | "
            f"WHS {row.warehouse} | "
            f"TRN {row.transaction_number} | "
            f"type={row.row_type} | "
            f"{row.description} | "
            f"qty={row.quantity} | "
            f"amount={row.amount} | "
            f"related_item="
            f"{row.related_item_number}"
        )

    return_rows = [
        row
        for row in rows
        if row.row_type == "return"
    ]

    print()
    print("Return samples:")

    for row in return_rows[:10]:
        print(
            f"- {row.purchase_date} | "
            f"WHS {row.warehouse} | "
            f"item={row.item_number} | "
            f"{row.description} | "
            f"qty={row.quantity} | "
            f"amount={row.amount}"
        )

    if result.failures:
        print()
        print("First unparsed rows:")

        for failure in result.failures[:20]:
            print()

            print(
                f"- {failure.purchase_date} | "
                f"WHS {failure.warehouse}"
            )

            print(
                f"  reason: "
                f"{failure.reason}"
            )

            print(
                f"  raw: "
                f"{failure.raw_text[:500]}"
            )


if __name__ == "__main__":
    main()