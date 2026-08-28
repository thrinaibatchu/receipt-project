from decimal import Decimal

import streamlit as st

from receipt_project.analytics.nl_sql import (
    ask_receipt_database,
)
from receipt_project.analytics.queries import (
    get_date_bounds,
    get_receipt_count,
    get_receipt_detail,
    get_recent_receipts,
    get_spend_by_store,
    get_spend_over_time,
    get_top_items_by_quantity,
    get_top_items_by_spend,
    get_total_spend,
    search_items,
)


def format_currency(value: Decimal) -> str:
    return f"${value:,.2f}"


def main() -> None:
    st.set_page_config(
        page_title="Receipt Dashboard",
        page_icon="🧾",
        layout="wide",
    )

    st.title("Receipt Dashboard")

    minimum_date, maximum_date = get_date_bounds()

    if minimum_date is None or maximum_date is None:
        st.info("No dated receipts are available.")
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
        st.error("From date must be on or before To date.")
        return

    receipt_count = get_receipt_count(
        start_date=start_date,
        end_date=end_date,
    )

    total_spend = get_total_spend(
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

    top_items_by_quantity = get_top_items_by_quantity(
        limit=10,
        start_date=start_date,
        end_date=end_date,
    )

    top_items_by_spend = get_top_items_by_spend(
        limit=10,
        start_date=start_date,
        end_date=end_date,
    )

    metric_col_1, metric_col_2 = st.columns(2)

    with metric_col_1:
        st.metric(
            label="Total Receipts",
            value=f"{receipt_count:,}",
        )

    with metric_col_2:
        st.metric(
            label="Total Spend",
            value=format_currency(total_spend),
        )

    st.subheader("Spend Over Time")

    chart_rows = [
        {
            "Date": row["purchase_date"],
            "Spend": float(row["total_spend"]),
        }
        for row in spend_over_time
    ]

    if chart_rows:
        st.line_chart(
            chart_rows,
            x="Date",
            y="Spend",
        )
    else:
        st.info("No receipts found in this date range.")

    st.subheader("Spend by Store")

    store_rows = [
        {
            "Store": store["store_name"],
            "Receipts": store["receipt_count"],
            "Total Spend": float(store["total_spend"]),
        }
        for store in spend_by_store
    ]

    st.dataframe(
        store_rows,
        width="stretch",
        hide_index=True,
        column_config={
            "Total Spend": st.column_config.NumberColumn(
                "Total Spend",
                format="$%.2f",
            ),
        },
    )

    st.subheader("Item Analytics")

    item_col_1, item_col_2 = st.columns(2)

    with item_col_1:
        st.markdown("#### Top Items by Quantity")

        quantity_rows = [
            {
                "Item": item["raw_description"],
                "Quantity": float(item["total_quantity"]),
            }
            for item in top_items_by_quantity
        ]

        st.dataframe(
            quantity_rows,
            width="stretch",
            hide_index=True,
        )

    with item_col_2:
        st.markdown("#### Top Items by Spend")

        spend_rows = [
            {
                "Item": item["raw_description"],
                "Spend": float(item["total_spend"]),
            }
            for item in top_items_by_spend
        ]

        st.dataframe(
            spend_rows,
            width="stretch",
            hide_index=True,
            column_config={
                "Spend": st.column_config.NumberColumn(
                    "Spend",
                    format="$%.2f",
                ),
            },
        )

    st.subheader("Search Items")

    search_text = st.text_input(
        "Item description",
        placeholder="Try MILK, EGGS, RICE...",
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
                    "Receipt ID": item["receipt_id"],
                    "Date": item["purchase_date"],
                    "Store": item["store_name"],
                    "Item Code": item["store_item_code"],
                    "Description": item["raw_description"],
                    "Quantity": float(item["quantity"]),
                    "Unit Price": (
                        float(item["unit_price"])
                        if item["unit_price"] is not None
                        else None
                    ),
                    "Total": float(item["total_price"]),
                }
                for item in item_matches
            ]

            st.dataframe(
                search_rows,
                width="stretch",
                hide_index=True,
                column_config={
                    "Unit Price": st.column_config.NumberColumn(
                        "Unit Price",
                        format="$%.2f",
                    ),
                    "Total": st.column_config.NumberColumn(
                        "Total",
                        format="$%.2f",
                    ),
                },
            )
        else:
            st.info("No matching items found.")

    st.subheader("Ask Your Receipts")

    question = st.text_input(
        "Ask a question about your receipt data",
        placeholder=(
            "Example: How much did I spend at Costco in 2026?"
        ),
        key="receipt_question",
    )

    ask_clicked = st.button(
        "Ask",
        type="primary",
    )

    if ask_clicked:
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            try:
                with st.spinner(
                    "Generating and running a read-only query..."
                ):
                    plan, columns, rows = ask_receipt_database(
                        question.strip()
                    )

                st.markdown("#### Result")

                if rows:
                    result_rows = [
                        dict(zip(columns, row))
                        for row in rows
                    ]

                    st.dataframe(
                        result_rows,
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.info(
                        "The query returned no rows."
                    )

                with st.expander(
                    "Show generated SQL and explanation"
                ):
                    st.markdown("**Generated SQL**")
                    st.code(
                        plan.sql,
                        language="sql",
                    )

                    st.markdown("**Explanation**")
                    st.write(
                        plan.explanation
                    )

            except Exception as exc:
                st.error(
                    f"Could not answer the question: {exc}"
                )

    st.subheader("Recent Receipts")

    recent_receipt_rows = [
        {
            "Receipt ID": receipt["id"],
            "Date": receipt["purchase_date"],
            "Store": receipt["store_name"],
            "Total": float(receipt["total"]),
        }
        for receipt in recent_receipts
    ]

    st.dataframe(
        recent_receipt_rows,
        width="stretch",
        hide_index=True,
        column_config={
            "Total": st.column_config.NumberColumn(
                "Total",
                format="$%.2f",
            ),
        },
    )

    receipt_ids = [
        receipt["id"]
        for receipt in recent_receipts
    ]

    if receipt_ids:
        selected_receipt_id = st.selectbox(
            "View receipt details",
            options=receipt_ids,
            format_func=lambda receipt_id: (
                f"Receipt {receipt_id}"
            ),
        )

        receipt_detail = get_receipt_detail(
            selected_receipt_id
        )

        if receipt_detail is not None:
            st.markdown(
                f"### {receipt_detail['store_name']} "
                f"— {receipt_detail['purchase_date']}"
            )

            detail_col_1, detail_col_2, detail_col_3 = (
                st.columns(3)
            )

            with detail_col_1:
                st.metric(
                    "Subtotal",
                    (
                        format_currency(
                            receipt_detail["subtotal"]
                        )
                        if receipt_detail["subtotal"] is not None
                        else "N/A"
                    ),
                )

            with detail_col_2:
                st.metric(
                    "Tax",
                    (
                        format_currency(
                            receipt_detail["tax"]
                        )
                        if receipt_detail["tax"] is not None
                        else "N/A"
                    ),
                )

            with detail_col_3:
                st.metric(
                    "Total",
                    format_currency(
                        receipt_detail["total"]
                    ),
                )

            st.markdown("#### Items")

            detail_item_rows = [
                {
                    "Item Code": item["store_item_code"],
                    "Description": item["raw_description"],
                    "Quantity": float(item["quantity"]),
                    "Unit Price": (
                        float(item["unit_price"])
                        if item["unit_price"] is not None
                        else None
                    ),
                    "Total": float(item["total_price"]),
                }
                for item in receipt_detail["items"]
            ]

            st.dataframe(
                detail_item_rows,
                width="stretch",
                hide_index=True,
                column_config={
                    "Unit Price": st.column_config.NumberColumn(
                        "Unit Price",
                        format="$%.2f",
                    ),
                    "Total": st.column_config.NumberColumn(
                        "Total",
                        format="$%.2f",
                    ),
                },
            )

            st.markdown("#### Discounts")

            if receipt_detail["discounts"]:
                discount_rows = [
                    {
                        "Description": discount[
                            "raw_description"
                        ],
                        "Amount": float(
                            discount["amount"]
                        ),
                        "Related Item Code": discount[
                            "related_item_code"
                        ],
                    }
                    for discount in receipt_detail[
                        "discounts"
                    ]
                ]

                st.dataframe(
                    discount_rows,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Amount": st.column_config.NumberColumn(
                            "Amount",
                            format="$%.2f",
                        ),
                    },
                )
            else:
                st.info(
                    "No discounts recorded for this receipt."
                )


if __name__ == "__main__":
    main()