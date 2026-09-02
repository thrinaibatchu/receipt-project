from datetime import date

from pydantic import BaseModel, Field


class ReceiptItem(BaseModel):
    store_item_code: str | None = Field(
        default=None,
        description=(
            "Store-specific item/SKU code printed "
            "separately from the product description"
        ),
    )

    raw_description: str = Field(
        description=(
            "Product description exactly as printed, "
            "excluding the store item code"
        ),
    )

    quantity: float = Field(
        default=1,
        ge=0,
        description=(
            "Absolute merchandise quantity. "
            "Transaction direction is determined by "
            "the signed receipt total."
        ),
    )

    unit_price: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Absolute price per unit when it can "
            "be determined"
        ),
    )

    total_price: float = Field(
        ge=0,
        description=(
            "Absolute merchandise line amount before "
            "separately printed discounts or adjustments"
        ),
    )


class ReceiptDiscount(BaseModel):
    raw_description: str = Field(
        description=(
            "Discount, coupon, instant savings, or "
            "refund adjustment line exactly as printed"
        ),
    )

    amount: float = Field(
        ge=0,
        description=(
            "Absolute adjustment amount. For purchase "
            "receipts it reduces merchandise subtotal; "
            "for refund receipts it reduces the "
            "absolute refund merchandise amount."
        ),
    )

    related_item_code: str | None = Field(
        default=None,
        description=(
            "Receipt item code this adjustment applies "
            "to, when identifiable"
        ),
    )


class Receipt(BaseModel):
    store_name: str = Field(
        description="Store or merchant name"
    )

    transaction_id: str | None = Field(
        default=None,
        description=(
            "Store transaction or receipt identifier "
            "when clearly printed"
        ),
    )

    purchase_date: date | None = Field(
        default=None,
        description=(
            "Receipt transaction date when clearly "
            "visible; otherwise null"
        ),
    )

    subtotal: float | None = Field(
        default=None,
        description=(
            "Signed receipt subtotal after adjustments "
            "and before tax. Refund subtotals are negative."
        ),
    )

    tax: float | None = Field(
        default=None,
        description=(
            "Signed total tax. Refund tax is negative."
        ),
    )

    total: float = Field(
        description=(
            "Signed final receipt total. Purchases are "
            "positive; refunds/returns are negative."
        ),
    )

    source_file: str = Field(
        description="Original receipt image filename"
    )

    items: list[ReceiptItem] = Field(
        description=(
            "Merchandise line items using absolute "
            "quantity and price magnitudes"
        ),
    )

    discounts: list[ReceiptDiscount] = Field(
        default_factory=list,
        description=(
            "Coupon, instant-savings, or refund "
            "adjustment lines"
        ),
    )
