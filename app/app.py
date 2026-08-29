from decimal import Decimal

import streamlit as st

from receipt_project.analytics.nl_sql import (
    ask_receipt_database,
)
from receipt_project.analytics.price_questions import (
    answer_price_question,
)
from receipt_project.analytics.queries import (
    get_date_bounds,
    get_receipt_detail,
    get_recent_receipts,
    get_spend_by_store,
    get_spend_over_time,
    get_top_items_by_quantity,
    get_top_items_by_spend,
    get_transaction_summary,
    search_items,
)


def format_currency(value: Decimal) -> str:
    return f"${value:,.2f}"


def render_price_question_result(
    intent,
    rows: list[dict],
) -> None:
    st.markdown("#### Result")

    if not rows:
        st.info(
            "No matching purchase-price observations were found."
        )
        return

    if intent.intent == "price_trend":
        st.markdown(
            f"**Effective unit-price history for "
            f"{intent.item}**"
        )

        st.caption(
            "Effective unit price includes linked "
            "item-level discounts when available."
        )

        chart_rows = [
            {
                "Date": row["purchase_date"],
                "Effective Unit Price": float(
                    row["effective_unit_price"]
                ),
            }
            for row in rows
        ]

        st.line_chart(
            chart_rows,
            x="Date",
            y="Effective Unit Price",
        )

        history_rows = [
            {
                "Date": row["purchase_date"],
                "Store": row["store_name"],
                "Item": row["raw_description"],
                "Item Code": row["store_item_code"],
                "Quantity": float(row["quantity"]),
                "Gross Line Price": float(
                    row["gross_line_price"]
                ),
                "Discount": float(
                    row["item_discount"]
                ),
                "Effective Line Price": float(
                    row["effective_line_price"]
                ),
                "Effective Unit Price": float(
                    row["effective_unit_price"]
                ),
            }
            for row in rows
        ]

        st.dataframe(
            history_rows,
            width="stretch",
            hide_index=True,
            column_config={
                "Gross Line Price": (
                    st.column_config.NumberColumn(
                        "Gross Line Price",
                        format="$%.2f",
                    )
                ),
                "Discount": (
                    st.column_config.NumberColumn(
                        "Discount",
                        format="$%.2f",
                    )
                ),
                "Effective Line Price": (
                    st.column_config.NumberColumn(
                        "Effective Line Price",
                        format="$%.2f",
                    )
                ),
                "Effective Unit Price": (
                    st.column_config.NumberColumn(
                        "Effective Unit Price",
                        format="$%.2f",
                    )
                ),
            },
        )

        return

    if intent.intent == "latest_across_stores":
        st.markdown(
            f"**Latest known effective price for "
            f"{intent.item} by store**"
        )

        st.caption(
            "Each row is the most recent matching "
            "purchase observation at that store."
        )

        latest_rows = [
            {
                "Store": row["store_name"],
                "Date": row["purchase_date"],
                "Item": row["raw_description"],
                "Item Code": row["store_item_code"],
                "Quantity": float(row["quantity"]),
                "Gross Line Price": float(
                    row["gross_line_price"]
                ),
                "Discount": float(
                    row["item_discount"]
                ),
                "Effective Unit Price": float(
                    row["effective_unit_price"]
                ),
            }
            for row in rows
        ]

        st.dataframe(
            latest_rows,
            width="stretch",
            hide_index=True,
            column_config={
                "Gross Line Price": (
                    st.column_config.NumberColumn(
                        "Gross Line Price",
                        format="$%.2f",
                    )
                ),
                "Discount": (
                    st.column_config.NumberColumn(
                        "Discount",
                        format="$%.2f",
                    )
                ),
                "Effective Unit Price": (
                    st.column_config.NumberColumn(
                        "Effective Unit Price",
                        format="$%.2f",
                    )
                ),
            },
        )

        return

    if intent.intent == "latest_at_store":
        row = rows[0]

        st.markdown(
            f"**Latest known effective price for "
            f"{intent.item} at {row['store_name']}**"
        )

        price_col, date_col, quantity_col = (
            st.columns(3)
        )

        with price_col:
            st.metric(
                "Effective Unit Price",
                format_currency(
                    row["effective_unit_price"]
                ),
            )

        with date_col:
            st.metric(
                "Purchase Date",
                str(row["purchase_date"]),
            )

        with quantity_col:
            st.metric(
                "Quantity Purchased",
                f"{row['quantity']}",
            )

        st.write(
            row["raw_description"]
        )

        detail_rows = [
            {
                "Store": row["store_name"],
                "Date": row["purchase_date"],
                "Item Code": row["store_item_code"],
                "Gross Line Price": float(
                    row["gross_line_price"]
                ),
                "Discount": float(
                    row["item_discount"]
                ),
                "Effective Line Price": float(
                    row["effective_line_price"]
                ),
                "Effective Unit Price": float(
                    row["effective_unit_price"]
                ),
            }
        ]

        st.dataframe(
            detail_rows,
            width="stretch",
            hide_index=True,
            column_config={
                "Gross Line Price": (
                    st.column_config.NumberColumn(
                        "Gross Line Price",
                        format="$%.2f",
                    )
                ),
                "Discount": (
                    st.column_config.NumberColumn(
                        "Discount",
                        format="$%.2f",
                    )
                ),
                "Effective Line Price": (
                    st.column_config.NumberColumn(
                        "Effective Line Price",
                        format="$%.2f",
                    )
                ),
                "Effective Unit Price": (
                    st.column_config.NumberColumn(
                        "Effective Unit Price",
                        format="$%.2f",
                    )
                ),
            },
        )


def main() -> None:
    st.set_page_config(
        page_title="Receipt Dashboard",
        page_icon="🧾",
        layout="wide",
    )

    st.title("Receipt Dashboard")

    minimum_date, maximum_date = get_date_bounds()

    if minimum_date is None or maximum_date is None:
        st.info("No dated transactions are available.")
        return

    st.subheader("Date Range")

    date_col_1, date_col_2 = st.columns(2)

    with date_col_1:
        start_date = st.date_input(
            "From",
            value=minimum_date,
            min_value=minimum_date,
            max_value=maximum_date,
        )

    with date_col_2:
        end_date = st.date_input(
            "To",
            value=maximum_date,
            min_value=minimum_date,
            max_value=maximum_date,
        )

    if start_date > end_date:
        st.error(
            "From date must be on or before To date."
        )
        return

    transaction_summary = get_transaction_summary(
        start_date=start_date,
        end_date=end_date,
    )

    recent_receipts = get_recent_receipts(
        limit=10,
        start_date=start_date,
        end_date=end_date,
    )

    spend_by_store = get_spend_by_store(
        start_date=start_date,
        end_date=end_date,
    )

    spend_over_time = get_spend_over_time(
        start_date=start_date,
        end_date=end_date,
    )

    top_items_by_quantity = (
        get_top_items_by_quantity(
            limit=10,
            start_date=start_date,
            end_date=end_date,
        )
    )

    top_items_by_spend = get_top_items_by_spend(
        limit=10,
        start_date=start_date,
        end_date=end_date,
    )

    (
        metric_col_1,
        metric_col_2,
        metric_col_3,
        metric_col_4,
    ) = st.columns(4)

    with metric_col_1:
        st.metric(
            label="Transactions",
            value=(
                f"{transaction_summary['transaction_count']:,}"
            ),
        )

    with metric_col_2:
        st.metric(
            label="Purchases",
            value=(
                f"{transaction_summary['purchase_count']:,}"
            ),
        )

    with metric_col_3:
        st.metric(
            label="Returns / Refunds",
            value=(
                f"{transaction_summary['return_count']:,}"
            ),
        )

    with metric_col_4:
        st.metric(
            label="Net Spend",
            value=format_currency(
                transaction_summary["net_spend"]
            ),
        )

    if transaction_summary["zero_total_count"]:
        st.caption(
            "Zero-value transactions in this range: "
            f"{transaction_summary['zero_total_count']:,}"
        )

    st.subheader("Net Spend Over Time")

    chart_rows = [
        {
            "Date": row["purchase_date"],
            "Net Spend": float(row["total_spend"]),
        }
        for row in spend_over_time
    ]

    if chart_rows:
        st.line_chart(
            chart_rows,
            x="Date",
            y="Net Spend",
        )
    else:
        st.info(
            "No transactions found in this date range."
        )

    st.subheader("Net Spend by Store")

    store_rows = [
        {
            "Store": store["store_name"],
            "Transactions": store[
                "transaction_count"
            ],
            "Purchases": store[
                "purchase_count"
            ],
            "Returns / Refunds": store[
                "return_count"
            ],
            "Net Spend": float(
                store["net_spend"]
            ),
        }
        for store in spend_by_store
    ]

    st.dataframe(
        store_rows,
        width="stretch",
        hide_index=True,
        column_config={
            "Net Spend": (
                st.column_config.NumberColumn(
                    "Net Spend",
                    format="$%.2f",
                )
            ),
        },
    )

    st.subheader("Item Analytics")

    item_col_1, item_col_2 = st.columns(2)

    with item_col_1:
        st.markdown(
            "#### Top Items by Net Quantity"
        )

        quantity_rows = [
            {
                "Item": item[
                    "raw_description"
                ],
                "Net Quantity": float(
                    item["total_quantity"]
                ),
            }
            for item
            in top_items_by_quantity
        ]

        st.dataframe(
            quantity_rows,
            width="stretch",
            hide_index=True,
        )

    with item_col_2:
        st.markdown(
            "#### Top Items by Net Item Spend"
        )

        spend_rows = [
            {
                "Item": item[
                    "raw_description"
                ],
                "Net Item Spend": float(
                    item["total_spend"]
                ),
            }
            for item in top_items_by_spend
        ]

        st.dataframe(
            spend_rows,
            width="stretch",
            hide_index=True,
            column_config={
                "Net Item Spend": (
                    st.column_config.NumberColumn(
                        "Net Item Spend",
                        format="$%.2f",
                    )
                ),
            },
        )

    st.subheader("Search Items")

    search_text = st.text_input(
        "Item description",
        placeholder=(
            "Try MILK, EGGS, RICE..."
        ),
    )

    if search_text.strip():
        item_matches = search_items(
            search_text=search_text,
            start_date=start_date,
            end_date=end_date,
        )

        if item_matches:
            search_rows = [
                {
                    "Transaction ID": item[
                        "receipt_id"
                    ],
                    "Date": item[
                        "purchase_date"
                    ],
                    "Store": item[
                        "store_name"
                    ],
                    "Item Code": item[
                        "store_item_code"
                    ],
                    "Description": item[
                        "raw_description"
                    ],
                    "Quantity": float(
                        item["quantity"]
                    ),
                    "Unit Price": (
                        float(
                            item["unit_price"]
                        )
                        if item[
                            "unit_price"
                        ] is not None
                        else None
                    ),
                    "Total": float(
                        item["total_price"]
                    ),
                }
                for item in item_matches
            ]

            st.dataframe(
                search_rows,
                width="stretch",
                hide_index=True,
                column_config={
                    "Unit Price": (
                        st.column_config.NumberColumn(
                            "Unit Price",
                            format="$%.2f",
                        )
                    ),
                    "Total": (
                        st.column_config.NumberColumn(
                            "Total",
                            format="$%.2f",
                        )
                    ),
                },
            )
        else:
            st.info(
                "No matching items found."
            )

    st.subheader(
        "Ask Your Receipt Data"
    )

    question = st.text_input(
        "Ask a question about your receipt data",
        placeholder=(
            "Example: What was the price trend "
            "for Andouille over time after discount?"
        ),
        key="receipt_question",
    )

    ask_clicked = st.button(
        "Ask",
        type="primary",
    )

    if ask_clicked:
        if not question.strip():
            st.warning(
                "Enter a question first."
            )
        else:
            try:
                with st.spinner(
                    "Understanding your question..."
                ):
                    price_intent, price_rows = (
                        answer_price_question(
                            question.strip()
                        )
                    )

                if (
                    price_intent.intent
                    != "not_price_question"
                ):
                    render_price_question_result(
                        price_intent,
                        price_rows,
                    )

                    with st.expander(
                        "Show interpreted question"
                    ):
                        st.write(
                            {
                                "intent": (
                                    price_intent.intent
                                ),
                                "item": (
                                    price_intent.item
                                ),
                                "store": (
                                    price_intent.store
                                ),
                            }
                        )

                else:
                    with st.spinner(
                        "Generating and running "
                        "a read-only query..."
                    ):
                        (
                            plan,
                            columns,
                            rows,
                        ) = ask_receipt_database(
                            question.strip()
                        )

                    st.markdown(
                        "#### Result"
                    )

                    if rows:
                        result_rows = [
                            dict(
                                zip(
                                    columns,
                                    row,
                                )
                            )
                            for row in rows
                        ]

                        st.dataframe(
                            result_rows,
                            width="stretch",
                            hide_index=True,
                        )
                    else:
                        st.info(
                            "The query returned "
                            "no rows."
                        )

                    with st.expander(
                        "Show generated SQL "
                        "and explanation"
                    ):
                        st.markdown(
                            "**Generated SQL**"
                        )

                        st.code(
                            plan.sql,
                            language="sql",
                        )

                        st.markdown(
                            "**Explanation**"
                        )

                        st.write(
                            plan.explanation
                        )

            except Exception as exc:
                st.error(
                    "Could not answer the "
                    f"question: {exc}"
                )

    st.subheader(
        "Recent Transactions"
    )

    recent_receipt_rows = [
        {
            "Transaction ID": receipt[
                "id"
            ],
            "Type": receipt[
                "transaction_type"
            ],
            "Date": receipt[
                "purchase_date"
            ],
            "Store": receipt[
                "store_name"
            ],
            "Total": float(
                receipt["total"]
            ),
        }
        for receipt in recent_receipts
    ]

    st.dataframe(
        recent_receipt_rows,
        width="stretch",
        hide_index=True,
        column_config={
            "Total": (
                st.column_config.NumberColumn(
                    "Total",
                    format="$%.2f",
                )
            ),
        },
    )

    receipt_ids = [
        receipt["id"]
        for receipt in recent_receipts
    ]

    if receipt_ids:
        selected_receipt_id = st.selectbox(
            "View transaction details",
            options=receipt_ids,
            format_func=lambda receipt_id: (
                f"Transaction {receipt_id}"
            ),
        )

        receipt_detail = get_receipt_detail(
            selected_receipt_id
        )

        if receipt_detail is not None:
            st.markdown(
                f"### "
                f"{receipt_detail['store_name']} "
                f"— "
                f"{receipt_detail['purchase_date']}"
            )

            st.caption(
                "Transaction type: "
                f"{receipt_detail['transaction_type']}"
            )

            (
                detail_col_1,
                detail_col_2,
                detail_col_3,
            ) = st.columns(3)

            with detail_col_1:
                st.metric(
                    "Subtotal",
                    (
                        format_currency(
                            receipt_detail[
                                "subtotal"
                            ]
                        )
                        if receipt_detail[
                            "subtotal"
                        ] is not None
                        else "N/A"
                    ),
                )

            with detail_col_2:
                st.metric(
                    "Tax",
                    (
                        format_currency(
                            receipt_detail[
                                "tax"
                            ]
                        )
                        if receipt_detail[
                            "tax"
                        ] is not None
                        else "N/A"
                    ),
                )

            with detail_col_3:
                st.metric(
                    "Total",
                    format_currency(
                        receipt_detail[
                            "total"
                        ]
                    ),
                )

            st.markdown(
                "#### Items"
            )

            detail_item_rows = [
                {
                    "Item Code": item[
                        "store_item_code"
                    ],
                    "Description": item[
                        "raw_description"
                    ],
                    "Quantity": float(
                        item["quantity"]
                    ),
                    "Unit Price": (
                        float(
                            item["unit_price"]
                        )
                        if item[
                            "unit_price"
                        ] is not None
                        else None
                    ),
                    "Total": float(
                        item["total_price"]
                    ),
                }
                for item
                in receipt_detail["items"]
            ]

            st.dataframe(
                detail_item_rows,
                width="stretch",
                hide_index=True,
                column_config={
                    "Unit Price": (
                        st.column_config.NumberColumn(
                            "Unit Price",
                            format="$%.2f",
                        )
                    ),
                    "Total": (
                        st.column_config.NumberColumn(
                            "Total",
                            format="$%.2f",
                        )
                    ),
                },
            )

            st.markdown(
                "#### Discounts"
            )

            if receipt_detail[
                "discounts"
            ]:
                discount_rows = [
                    {
                        "Description": (
                            discount[
                                "raw_description"
                            ]
                        ),
                        "Amount": float(
                            discount[
                                "amount"
                            ]
                        ),
                        "Related Item Code": (
                            discount[
                                "related_item_code"
                            ]
                        ),
                    }
                    for discount
                    in receipt_detail[
                        "discounts"
                    ]
                ]

                st.dataframe(
                    discount_rows,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Amount": (
                            st.column_config.NumberColumn(
                                "Amount",
                                format="$%.2f",
                            )
                        ),
                    },
                )
            else:
                st.info(
                    "No discounts recorded for "
                    "this transaction."
                )


if __name__ == "__main__":
    main()