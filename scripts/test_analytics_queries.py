from receipt_project.analytics.queries import (
    get_receipt_count,
    get_receipt_detail,
    get_recent_receipts,
    get_spend_by_store,
    get_top_items_by_quantity,
    get_top_items_by_spend,
    get_total_spend,
    search_items,
)


def main() -> None:
    receipt_count = get_receipt_count()
    total_spend = get_total_spend()
    recent_receipts = get_recent_receipts(limit=5)
    spend_by_store = get_spend_by_store()
    top_quantity = get_top_items_by_quantity(limit=5)
    top_spend = get_top_items_by_spend(limit=5)

    print(f"Receipt count: {receipt_count}")
    print(f"Total spend: {total_spend}")

    print()
    print("Recent receipts:")

    for receipt in recent_receipts:
        print(
            f"- id={receipt['id']} | "
            f"{receipt['purchase_date']} | "
            f"{receipt['store_name']} | "
            f"${receipt['total']}"
        )

    print()
    print("Spend by store:")

    for store in spend_by_store:
        print(
            f"- {store['store_name']} | "
            f"receipts={store['receipt_count']} | "
            f"spend=${store['total_spend']}"
        )

    print()
    print("Top items by quantity:")

    for item in top_quantity:
        print(
            f"- {item['raw_description']} | "
            f"qty={item['total_quantity']}"
        )

    print()
    print("Top items by spend:")

    for item in top_spend:
        print(
            f"- {item['raw_description']} | "
            f"spend=${item['total_spend']}"
        )

    print()
    print("Search for MILK:")

    results = search_items("MILK")

    for item in results:
        print(
            f"- receipt={item['receipt_id']} | "
            f"{item['purchase_date']} | "
            f"{item['raw_description']} | "
            f"qty={item['quantity']} | "
            f"total=${item['total_price']}"
        )

    if recent_receipts:
        receipt_id = recent_receipts[0]["id"]
        detail = get_receipt_detail(receipt_id)

        print()
        print(f"Receipt detail for id={receipt_id}:")

        if detail:
            print(
                f"- {detail['purchase_date']} | "
                f"{detail['store_name']} | "
                f"${detail['total']}"
            )
            print(f"- items={len(detail['items'])}")
            print(f"- discounts={len(detail['discounts'])}")


if __name__ == "__main__":
    main()