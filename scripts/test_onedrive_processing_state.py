from receipt_project.onedrive import (
    list_receipt_files,
    move_receipt_to_processed,
)


TEST_FILENAME = "receipt_002.pdf"


def main():
    before = list_receipt_files()

    before_names = {
        item["name"]
        for item in before
    }

    if TEST_FILENAME not in before_names:
        raise RuntimeError(
            f"{TEST_FILENAME} is not present in /Receipts"
        )

    print(f"Pending before move: {TEST_FILENAME}")

    moved = move_receipt_to_processed(TEST_FILENAME)

    print("Move to /Receipts/processed: SUCCESS")
    print(
        "File ID returned:",
        "YES" if moved.get("id") else "NO",
    )

    after = list_receipt_files()

    after_names = {
        item["name"]
        for item in after
    }

    if TEST_FILENAME in after_names:
        raise RuntimeError(
            f"{TEST_FILENAME} is still being returned "
            "as a pending receipt."
        )

    print("Pending-list removal: SUCCESS")
    print(f"Receipt candidates remaining: {len(after)}")


if __name__ == "__main__":
    main()
