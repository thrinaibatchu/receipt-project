import sys
from pathlib import Path

from receipt_project.database.writer import insert_receipt
from receipt_project.extraction.gemini import extract_receipt
from receipt_project.validation.receipt_checks import validate_receipt_totals


def ingest_receipt(file_path: Path) -> None:
    print(f"Processing receipt: {file_path}")

    receipt = extract_receipt(file_path)

    print(
        f"Extracted: {receipt.store_name} "
        f"- {receipt.purchase_date}"
    )

    issues = validate_receipt_totals(receipt)

    if issues:
        print()
        print("Receipt requires review:")

        for issue in issues:
            print(f"  - {issue}")

        return

    receipt_id = insert_receipt(receipt)

    print()
    print(
        f"Receipt inserted successfully "
        f"with id={receipt_id}"
    )


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: uv run python -m receipt_project.ingest "
            "<receipt-file>"
        )
        raise SystemExit(1)

    file_path = Path(sys.argv[1])

    ingest_receipt(file_path)


if __name__ == "__main__":
    main()