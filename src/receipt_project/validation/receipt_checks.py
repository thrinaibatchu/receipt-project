from receipt_project.models.receipt import Receipt


def validate_receipt_totals(
    receipt: Receipt,
) -> list[str]:
    issues: list[str] = []

    items_total = sum(
        item.total_price
        for item in receipt.items
    )

    discounts_total = sum(
        discount.amount
        for discount in receipt.discounts
    )

    transaction_sign = (
        -1
        if receipt.total < 0
        else 1
    )

    calculated_subtotal = (
        transaction_sign
        * (
            items_total
            - discounts_total
        )
    )

    if receipt.subtotal is not None:
        difference = abs(
            calculated_subtotal
            - receipt.subtotal
        )

        if difference > 0.02:
            issues.append(
                "Items minus adjustments do not "
                "match signed subtotal: "
                f"items={items_total:.2f}, "
                f"adjustments={discounts_total:.2f}, "
                f"calculated={calculated_subtotal:.2f}, "
                f"subtotal={receipt.subtotal:.2f}"
            )

    if (
        receipt.subtotal is not None
        and receipt.tax is not None
    ):
        expected_total = (
            receipt.subtotal
            + receipt.tax
        )

        difference = abs(
            expected_total
            - receipt.total
        )

        if difference > 0.02:
            issues.append(
                "Subtotal + tax does not match total: "
                f"expected={expected_total:.2f}, "
                f"total={receipt.total:.2f}"
            )

    return issues
