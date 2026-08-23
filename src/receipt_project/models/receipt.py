from datetime import date

from pydantic import BaseModel, Field


class ReceiptItem(BaseModel):
    raw_description: str = Field(
        description="Item description exactly as printed on the receipt"
    )

    quantity: float = Field(
        default=1,
        ge=0,
        description="Quantity purchased"
    )

    unit_price: float | None = Field(
        default=None,
        ge=0,
        description="Price per unit when it can be determined"
    )

    total_price: float = Field(
        ge=0,
        description="Total amount charged for this item before discounts"
    )


class ReceiptDiscount(BaseModel):
    raw_description: str = Field(
        description="Discount or coupon line exactly as printed on the receipt"
    )

    amount: float = Field(
        ge=0,
        description="Positive discount amount to subtract from item totals"
    )

    related_item_code: str | None = Field(
        default=None,
        description="Receipt item code this discount applies to, when identifiable"
    )


class Receipt(BaseModel):
    store_name: str = Field(
        description="Store or merchant name"
    )

    purchase_date: date = Field(
        description="Receipt transaction date"
    )

    subtotal: float | None = Field(
        default=None,
        ge=0,
        description="Receipt subtotal after discounts and before tax"
    )

    tax: float | None = Field(
        default=None,
        ge=0,
        description="Total tax charged"
    )

    total: float = Field(
        ge=0,
        description="Final receipt total"
    )

    source_file: str = Field(
        description="Original receipt image filename"
    )

    items: list[ReceiptItem] = Field(
        description="Purchased merchandise line items"
    )

    discounts: list[ReceiptDiscount] = Field(
        default_factory=list,
        description="Discount, coupon, or instant-savings lines"
    )
