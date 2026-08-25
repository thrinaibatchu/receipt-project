import sys
from enum import Enum
from pathlib import Path

from receipt_project.database.writer import (
    find_receipt_by_source_hash,
    insert_receipt,
)
from receipt_project.extraction.gemini import extract_receipt
from receipt_project.identity import (
    calculate_receipt_fingerprint,
    calculate_source_hash,
)
from receipt_project.validation.receipt_checks import (
    validate_receipt_totals,
)


class IngestStatus(str, Enum):
    INSERTED = "inserted"
    DUPLICATE = "duplicate"
    REVIEW_REQUIRED = "review_required"


def ingest_receipt(file_path: Path) -> IngestStatus:
    print(f"Processing receipt: {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(
            f"Receipt file not found: {file_path}"
        )

    # Step 1: hash the raw file before calling Gemini
    source_hash = calculate_source_hash(file_path)

    # Step 2: skip exact duplicate files immediately
    existing = find_receipt_by_source_hash(source_hash)

    if existing:
        print(
            "Duplicate file detected. "
            f"Existing receipt id={existing[0]}, "
            f"source_file={existing[1]}"
        )

        return IngestStatus.DUPLICATE

    # Step 3: only call Gemini for a new source file
    receipt = extract_receipt(file_path)

    print(
        f"Extracted: {receipt.store_name} "
        f"- {receipt.purchase_date}"
    )

    # Step 4: quality validation
    issues = validate_receipt_totals(receipt)

    if issues:
        print()
        print("Receipt requires review:")

        for issue in issues:
            print(f"  - {issue}")

        return IngestStatus.REVIEW_REQUIRED

    # Step 5: calculate logical identity after extraction
    receipt_fingerprint = calculate_receipt_fingerprint(
        receipt
    )

    # Step 6: database insertion
    receipt_id = insert_receipt(
        receipt,
        source_hash,
        receipt_fingerprint,
    )

    print()
    print(
        f"Receipt inserted successfully "
        f"with id={receipt_id}"
    )

    return IngestStatus.INSERTED


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: uv run python -m receipt_project.ingest "
            "<receipt-file>"
        )
        raise SystemExit(1)

    file_path = Path(sys.argv[1])

    status = ingest_receipt(file_path)

    if status == IngestStatus.REVIEW_REQUIRED:
        raise SystemExit(2)


if __name__ == "__main__":
    main()