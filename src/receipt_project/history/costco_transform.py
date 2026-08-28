from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from receipt_project.history.costco_statement import (
    COUPON_TYPES,
    CostcoHistoryRow,
    parse_costco_history_pdf,
)


@dataclass(frozen=True)
class HistoricalReceipt:
    historical_key: str
    store_name: str
    purchase_date: date
    source_type: str
    warehouse_number: str
    register_number: str
    historical_transaction_number: str
    transaction_time: str | None
    source_file: str
    calculated_total: Decimal

    items: list["HistoricalReceiptItem"]
    discounts: list["HistoricalReceiptDiscount"]


@dataclass(frozen=True)
class HistoricalReceiptItem:
    source_row_number: int
    store_item_code: str | None
    raw_description: str
    quantity: Decimal
    total_price: Decimal
    historical_row_type: str


@dataclass(frozen=True)
class HistoricalReceiptDiscount:
    source_row_number: int
    raw_description: str
    amount: Decimal
    related_item_code: str | None
    historical_row_type: str


def build_historical_key(
    *,
    warehouse: str,
    purchase_date: date,
    register: str,
    transaction_number: str,
) -> str:
    raw_key = (
        "costco_shopping_history|"
        f"{warehouse}|"
        f"{purchase_date.isoformat()}|"
        f"{register}|"
        f"{transaction_number}"
    )

    digest = hashlib.sha256(
        raw_key.encode("utf-8")
    ).hexdigest()

    return digest


def get_transaction_time(
    rows: list[CostcoHistoryRow],
) -> str | None:
    times = {
        row.transaction_time
        for row in rows
        if row.transaction_time is not None
    }

    if not times:
        return None

    if len(times) != 1:
        raise ValueError(
            "Historical transaction contains "
            f"multiple transaction times: {sorted(times)}"
        )

    return next(iter(times))


def build_historical_receipts(
    pdf_path: str | Path,
) -> list[HistoricalReceipt]:
    path = Path(
        pdf_path
    ).expanduser().resolve()

    result = parse_costco_history_pdf(
        path
    )

    if result.failures:
        raise RuntimeError(
            "Historical transformation requires "
            "a fully parsed source. "
            f"Unparsed rows: {len(result.failures)}"
        )

    rows_by_transaction: dict[
        tuple[str, date, str, str],
        list[CostcoHistoryRow],
    ] = defaultdict(list)

    for row in result.rows:
        rows_by_transaction[
            row.transaction_key
        ].append(row)

    receipts: list[HistoricalReceipt] = []

    for transaction_key, rows in sorted(
        rows_by_transaction.items(),
        key=lambda item: (
            item[0][1],
            item[0][0],
            item[0][2],
            item[0][3],
        ),
    ):
        (
            warehouse,
            purchase_date,
            register,
            transaction_number,
        ) = transaction_key

        items: list[
            HistoricalReceiptItem
        ] = []

        discounts: list[
            HistoricalReceiptDiscount
        ] = []

        calculated_total = Decimal("0")

        for row in rows:
            calculated_total += row.amount

            if row.row_type in COUPON_TYPES:
                discounts.append(
                    HistoricalReceiptDiscount(
                        source_row_number=(
                            row.source_row_number
                        ),
                        raw_description=(
                            row.description
                        ),
                        amount=row.amount,
                        related_item_code=(
                            row.related_item_number
                        ),
                        historical_row_type=(
                            row.row_type
                        ),
                    )
                )

                continue

            items.append(
                HistoricalReceiptItem(
                    source_row_number=(
                        row.source_row_number
                    ),
                    store_item_code=(
                        row.item_number
                    ),
                    raw_description=(
                        row.description
                    ),
                    quantity=row.quantity,
                    total_price=row.amount,
                    historical_row_type=(
                        row.row_type
                    ),
                )
            )

        receipts.append(
            HistoricalReceipt(
                historical_key=build_historical_key(
                    warehouse=warehouse,
                    purchase_date=purchase_date,
                    register=register,
                    transaction_number=(
                        transaction_number
                    ),
                ),
                store_name="Costco Wholesale",
                purchase_date=purchase_date,
                source_type=(
                    "costco_shopping_history"
                ),
                warehouse_number=warehouse,
                register_number=register,
                historical_transaction_number=(
                    transaction_number
                ),
                transaction_time=(
                    get_transaction_time(rows)
                ),
                source_file=path.name,
                calculated_total=(
                    calculated_total
                ),
                items=items,
                discounts=discounts,
            )
        )

    return receipts