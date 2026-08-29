from __future__ import annotations

from datetime import date

import psycopg

from receipt_project.analytics.queries import (
    get_database_url,
    normalize_store_name,
)


ITEM_PRICE_CTE = """
WITH item_lines AS (
    SELECT
        r.id AS receipt_id,
        r.purchase_date,
        r.store_name,
        r.source_type,
        ri.store_item_code,
        ri.raw_description,
        SUM(ri.quantity) AS quantity,
        SUM(ri.total_price) AS gross_line_price
    FROM receipt_items ri
    JOIN receipts r
      ON r.id = ri.receipt_id
    WHERE r.total > 0
      AND ri.quantity > 0
    GROUP BY
        r.id,
        r.purchase_date,
        r.store_name,
        r.source_type,
        ri.store_item_code,
        ri.raw_description
),
item_discounts AS (
    SELECT
        rd.receipt_id,
        rd.related_item_code,
        SUM(
            CASE
                WHEN r.source_type = 'live_receipt'
                THEN -ABS(rd.amount)

                WHEN (
                    r.source_type =
                        'costco_shopping_history'
                    AND rd.historical_row_type =
                        'coupon_discount'
                )
                THEN rd.amount

                ELSE 0
            END
        ) AS item_discount
    FROM receipt_discounts rd
    JOIN receipts r
      ON r.id = rd.receipt_id
    WHERE rd.related_item_code IS NOT NULL
    GROUP BY
        rd.receipt_id,
        rd.related_item_code
),
item_prices AS (
    SELECT
        il.receipt_id,
        il.purchase_date,
        il.store_name,
        il.source_type,
        il.store_item_code,
        il.raw_description,
        il.quantity,
        il.gross_line_price,
        COALESCE(
            d.item_discount,
            0
        ) AS item_discount,
        (
            il.gross_line_price
            + COALESCE(
                d.item_discount,
                0
            )
        ) AS effective_line_price,
        (
            il.gross_line_price
            + COALESCE(
                d.item_discount,
                0
            )
        ) / NULLIF(
            il.quantity,
            0
        ) AS effective_unit_price
    FROM item_lines il
    LEFT JOIN item_discounts d
      ON d.receipt_id = il.receipt_id
     AND d.related_item_code
         = il.store_item_code
)
"""


def row_to_observation(
    row: tuple,
) -> dict:
    observation = {
        "receipt_id": row[0],
        "purchase_date": row[1],
        "store_name": normalize_store_name(
            row[2]
        ),
        "raw_store_name": row[2],
        "source_type": row[3],
        "store_item_code": row[4],
        "raw_description": row[5],
        "quantity": row[6],
        "gross_line_price": row[7],
        "item_discount": row[8],
        "effective_line_price": row[9],
        "effective_unit_price": row[10],
    }

    verify_price_observation(
        observation
    )

    return observation


def verify_price_observation(
    observation: dict,
) -> None:
    quantity = observation["quantity"]

    gross_line_price = observation[
        "gross_line_price"
    ]

    item_discount = observation[
        "item_discount"
    ]

    effective_line_price = observation[
        "effective_line_price"
    ]

    effective_unit_price = observation[
        "effective_unit_price"
    ]

    if quantity <= 0:
        raise RuntimeError(
            "Price observation contains "
            "non-positive quantity."
        )

    if item_discount > 0:
        raise RuntimeError(
            "Normalized purchase discount "
            "must not increase item price."
        )

    expected_line_price = (
        gross_line_price
        + item_discount
    )

    if (
        effective_line_price
        != expected_line_price
    ):
        raise RuntimeError(
            "Effective line price calculation "
            "is inconsistent."
        )

    expected_unit_price = (
        effective_line_price
        / quantity
    )

    if (
        effective_unit_price
        != expected_unit_price
    ):
        raise RuntimeError(
            "Effective unit price calculation "
            "is inconsistent."
        )


def get_item_price_history(
    search_text: str,
    store_name: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 500,
) -> list[dict]:
    search_pattern = (
        f"%{search_text.strip()}%"
    )

    store_pattern = (
        f"%{store_name.strip()}%"
        if store_name
        else None
    )

    sql = (
        ITEM_PRICE_CTE
        + """
        SELECT
            receipt_id,
            purchase_date,
            store_name,
            source_type,
            store_item_code,
            raw_description,
            quantity,
            gross_line_price,
            item_discount,
            effective_line_price,
            effective_unit_price
        FROM item_prices
        WHERE raw_description ILIKE %s
          AND (
              %s::date IS NULL
              OR purchase_date >= %s::date
          )
          AND (
              %s::date IS NULL
              OR purchase_date <= %s::date
          )
          AND (
              %s::text IS NULL
              OR store_name ILIKE %s
          )
        ORDER BY
            purchase_date,
            receipt_id,
            store_item_code
        LIMIT %s
        """
    )

    with psycopg.connect(
        get_database_url()
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                (
                    search_pattern,
                    start_date,
                    start_date,
                    end_date,
                    end_date,
                    store_pattern,
                    store_pattern,
                    limit,
                ),
            )

            rows = cursor.fetchall()

    return [
        row_to_observation(row)
        for row in rows
    ]


def get_latest_item_prices_by_store(
    search_text: str,
) -> list[dict]:
    """
    Return the latest matching effective item price
    for each normalized store.

    This answers questions such as:

    "What is the latest price for Okra across stores?"
    """

    search_pattern = (
        f"%{search_text.strip()}%"
    )

    sql = (
        ITEM_PRICE_CTE
        + """
        SELECT DISTINCT ON (
            UPPER(TRIM(store_name))
        )
            receipt_id,
            purchase_date,
            store_name,
            source_type,
            store_item_code,
            raw_description,
            quantity,
            gross_line_price,
            item_discount,
            effective_line_price,
            effective_unit_price
        FROM item_prices
        WHERE raw_description ILIKE %s
        ORDER BY
            UPPER(TRIM(store_name)),
            purchase_date DESC NULLS LAST,
            receipt_id DESC
        """
    )

    with psycopg.connect(
        get_database_url()
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                (search_pattern,),
            )

            rows = cursor.fetchall()

    observations = [
        row_to_observation(row)
        for row in rows
    ]

    return sorted(
        observations,
        key=lambda row: (
            row["store_name"],
            row["purchase_date"],
        ),
    )


def get_latest_item_price_at_store(
    search_text: str,
    store_name: str,
) -> dict | None:
    """
    Return the latest matching effective item price
    at a particular store.

    This answers questions such as:

    "What is the latest price for Okra at Costco?"
    """

    search_pattern = (
        f"%{search_text.strip()}%"
    )

    store_pattern = (
        f"%{store_name.strip()}%"
    )

    sql = (
        ITEM_PRICE_CTE
        + """
        SELECT
            receipt_id,
            purchase_date,
            store_name,
            source_type,
            store_item_code,
            raw_description,
            quantity,
            gross_line_price,
            item_discount,
            effective_line_price,
            effective_unit_price
        FROM item_prices
        WHERE raw_description ILIKE %s
          AND store_name ILIKE %s
        ORDER BY
            purchase_date DESC NULLS LAST,
            receipt_id DESC
        LIMIT 1
        """
    )

    with psycopg.connect(
        get_database_url()
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                (
                    search_pattern,
                    store_pattern,
                ),
            )

            row = cursor.fetchone()

    if row is None:
        return None

    return row_to_observation(
        row
    )


def get_discounted_purchase_samples(
    limit: int = 20,
) -> list[dict]:
    sql = (
        ITEM_PRICE_CTE
        + """
        SELECT
            receipt_id,
            purchase_date,
            store_name,
            source_type,
            store_item_code,
            raw_description,
            quantity,
            gross_line_price,
            item_discount,
            effective_line_price,
            effective_unit_price
        FROM item_prices
        WHERE item_discount < 0
        ORDER BY
            purchase_date DESC,
            receipt_id DESC
        LIMIT %s
        """
    )

    with psycopg.connect(
        get_database_url()
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                (limit,),
            )

            rows = cursor.fetchall()

    return [
        row_to_observation(row)
        for row in rows
    ]