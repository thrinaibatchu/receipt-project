from __future__ import annotations

import psycopg

from receipt_project.history.costco_transform import (
    HistoricalReceipt,
)


def build_transaction_id(
    receipt: HistoricalReceipt,
) -> str:
    return (
        "costco-history:"
        f"{receipt.warehouse_number}:"
        f"{receipt.purchase_date.isoformat()}:"
        f"{receipt.register_number}:"
        f"{receipt.historical_transaction_number}"
    )


def find_existing_historical_keys(
    conn: psycopg.Connection,
    receipts: list[HistoricalReceipt],
) -> list[str]:
    historical_keys = [
        receipt.historical_key
        for receipt in receipts
    ]

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT historical_key
            FROM receipts
            WHERE historical_key = ANY(%s)
            ORDER BY historical_key;
            """,
            (historical_keys,),
        )

        return [
            row[0]
            for row in cur.fetchall()
        ]


def insert_historical_receipt(
    conn: psycopg.Connection,
    receipt: HistoricalReceipt,
) -> int:
    transaction_id = build_transaction_id(
        receipt
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO receipts (
                store_name,
                purchase_date,
                subtotal,
                tax,
                total,
                transaction_id,
                source_file,
                source_hash,
                receipt_fingerprint,
                source_type,
                warehouse_number,
                register_number,
                historical_transaction_number,
                transaction_time,
                historical_key
            )
            VALUES (
                %s,
                %s,
                NULL,
                NULL,
                %s,
                %s,
                %s,
                NULL,
                NULL,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING id;
            """,
            (
                receipt.store_name,
                receipt.purchase_date,
                receipt.calculated_total,
                transaction_id,
                receipt.source_file,
                receipt.source_type,
                receipt.warehouse_number,
                receipt.register_number,
                receipt.historical_transaction_number,
                receipt.transaction_time,
                receipt.historical_key,
            ),
        )

        receipt_id = cur.fetchone()[0]

        for item in receipt.items:
            cur.execute(
                """
                INSERT INTO receipt_items (
                    receipt_id,
                    product_id,
                    store_item_code,
                    raw_description,
                    quantity,
                    unit_price,
                    total_price,
                    source_row_number,
                    historical_row_type
                )
                VALUES (
                    %s,
                    NULL,
                    %s,
                    %s,
                    %s,
                    NULL,
                    %s,
                    %s,
                    %s
                );
                """,
                (
                    receipt_id,
                    item.store_item_code,
                    item.raw_description,
                    item.quantity,
                    item.total_price,
                    item.source_row_number,
                    item.historical_row_type,
                ),
            )

        for discount in receipt.discounts:
            cur.execute(
                """
                INSERT INTO receipt_discounts (
                    receipt_id,
                    raw_description,
                    amount,
                    related_item_code,
                    source_row_number,
                    historical_row_type
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                );
                """,
                (
                    receipt_id,
                    discount.raw_description,
                    discount.amount,
                    discount.related_item_code,
                    discount.source_row_number,
                    discount.historical_row_type,
                ),
            )

    return receipt_id