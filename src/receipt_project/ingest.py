import sys
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from receipt_project.database.writer import (
    find_receipt_by_source_hash,
    insert_receipt,
)
from receipt_project.extraction.gemini import (
    extract_receipt,
    repair_receipt_extraction,
)
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


def ingest_receipt(
    file_path: Path,
    extraction_json_callback: Callable[[str], None] | None = None,
) -> IngestStatus:
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

    # Step 3: extract a new source file
    receipt = extract_receipt(file_path)

    print(
        f"Extracted: {receipt.store_name} "
        f"- {receipt.purchase_date}"
    )

    # Step 4: perform strict arithmetic validation.
    issues = validate_receipt_totals(receipt)

    # Step 5: if the first extraction does not reconcile, give the
    # extraction provider one targeted opportunity to re-read the
    # original receipt using the exact validation failures.
    if issues:
        print()
        print(
            "Initial extraction failed validation. "
            "Attempting one repair pass."
        )

        for issue in issues:
            print(f"  - {issue}")

        repaired_receipt = repair_receipt_extraction(
            file_path=file_path,
            receipt=receipt,
            validation_issues=issues,
        )

        repaired_issues = validate_receipt_totals(
            repaired_receipt
        )

        if not repaired_issues:
            receipt = repaired_receipt
            issues = []

            print(
                "Repair pass produced a valid extraction."
            )

        else:
            receipt = repaired_receipt
            issues = repaired_issues

            print(
                "Repair pass still requires review."
            )

    # Step 6: persist the final structured extraction before routing.
    #
    # If a repair pass occurred, this stores the repaired extraction.
    # If the repair still fails validation, the final attempted
    # extraction is retained for review/debugging.
    if extraction_json_callback is not None:
        extraction_json = receipt.model_dump_json(
            indent=2,
        )

        extraction_json_callback(
            extraction_json
        )

        print(
            "Structured extraction JSON persisted."
        )

    # Step 7: quarantine unresolved validation failures
    if issues:
        print()
        print("Receipt requires review:")

        for issue in issues:
            print(f"  - {issue}")

        return IngestStatus.REVIEW_REQUIRED

    # Step 8: calculate logical identity after extraction
    receipt_fingerprint = calculate_receipt_fingerprint(
        receipt
    )

    # Step 9: database insertion
    try:
        receipt_id = insert_receipt(
            receipt,
            source_hash,
            receipt_fingerprint,
        )

    except ValueError as exc:
        if str(exc).startswith(
            "Duplicate receipt detected."
        ):
            print()
            print(str(exc))

            return IngestStatus.DUPLICATE

        raise

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