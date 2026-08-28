from __future__ import annotations

import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

from receipt_project.history.costco_transform import (
    build_historical_receipts,
)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: "
            "uv run python "
            "scripts/dry_run_costco_history_import.py "
            "<costco-history.pdf>"
        )

    pdf_path = Path(
        sys.argv[1]
    ).expanduser()

    receipts = build_historical_receipts(
        pdf_path
    )

    total_items = sum(
        len(receipt.items)
        for receipt in receipts
    )

    total_discounts = sum(
        len(receipt.discounts)
        for receipt in receipts
    )

    receipt_totals = [
        receipt.calculated_total
        for receipt in receipts
    ]

    item_type_counts = Counter(
        item.historical_row_type
        for receipt in receipts
        for item in receipt.items
    )

    discount_type_counts = Counter(
        discount.historical_row_type
        for receipt in receipts
        for discount in receipt.discounts
    )

    historical_keys = [
        receipt.historical_key
        for receipt in receipts
    ]

    duplicate_keys = (
        len(historical_keys)
        - len(set(historical_keys))
    )

    zero_total_receipts = [
        receipt
        for receipt in receipts
        if receipt.calculated_total
        == Decimal("0")
    ]

    negative_total_receipts = [
        receipt
        for receipt in receipts
        if receipt.calculated_total
        < Decimal("0")
    ]

    positive_total_receipts = [
        receipt
        for receipt in receipts
        if receipt.calculated_total
        > Decimal("0")
    ]

    print()
    print("Costco historical import dry run")
    print("--------------------------------")

    print(
        f"Receipts to create: {len(receipts)}"
    )

    print(
        f"Receipt items to create: {total_items}"
    )

    print(
        "Receipt discounts to create: "
        f"{total_discounts}"
    )

    print(
        f"Duplicate historical keys: "
        f"{duplicate_keys}"
    )

    print()
    print("Historical item row types:")

    for row_type in (
        "purchase",
        "return",
        "adjustment",
    ):
        print(
            f"- {row_type}: "
            f"{item_type_counts[row_type]}"
        )

    print()
    print("Historical discount row types:")

    for row_type in (
        "coupon_discount",
        "coupon_reversal",
        "coupon_adjustment",
    ):
        print(
            f"- {row_type}: "
            f"{discount_type_counts[row_type]}"
        )

    print()
    print("Calculated transaction totals:")

    print(
        "- positive: "
        f"{len(positive_total_receipts)}"
    )

    print(
        "- negative: "
        f"{len(negative_total_receipts)}"
    )

    print(
        "- zero: "
        f"{len(zero_total_receipts)}"
    )

    if receipt_totals:
        print(
            "- min: "
            f"{min(receipt_totals)}"
        )

        print(
            "- max: "
            f"{max(receipt_totals)}"
        )

        print(
            "- net across all transactions: "
            f"{sum(receipt_totals, Decimal('0'))}"
        )

    print()
    print("First 10 transformed transactions:")

    for receipt in receipts[:10]:
        print(
            f"- {receipt.purchase_date} | "
            f"WHS {receipt.warehouse_number} | "
            f"REG {receipt.register_number} | "
            f"TRN "
            f"{receipt.historical_transaction_number} | "
            f"items={len(receipt.items)} | "
            f"discounts={len(receipt.discounts)} | "
            f"calculated_total="
            f"{receipt.calculated_total} | "
            f"key={receipt.historical_key[:12]}"
        )

    if negative_total_receipts:
        print()
        print(
            "First 10 negative-total transactions:"
        )

        for receipt in negative_total_receipts[
            :10
        ]:
            print(
                f"- {receipt.purchase_date} | "
                f"WHS {receipt.warehouse_number} | "
                f"REG {receipt.register_number} | "
                f"TRN "
                f"{receipt.historical_transaction_number} | "
                f"total={receipt.calculated_total} | "
                f"items={len(receipt.items)} | "
                f"discounts={len(receipt.discounts)}"
            )

    if zero_total_receipts:
        print()
        print(
            "First 10 zero-total transactions:"
        )

        for receipt in zero_total_receipts[
            :10
        ]:
            print(
                f"- {receipt.purchase_date} | "
                f"WHS {receipt.warehouse_number} | "
                f"REG {receipt.register_number} | "
                f"TRN "
                f"{receipt.historical_transaction_number} | "
                f"items={len(receipt.items)} | "
                f"discounts={len(receipt.discounts)}"
            )


if __name__ == "__main__":
    main()