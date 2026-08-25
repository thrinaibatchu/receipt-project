import sys
import tempfile
from enum import Enum
from pathlib import Path

from receipt_project.ingest import (
    IngestStatus,
    ingest_receipt,
)
from receipt_project.onedrive import (
    download_drive_item,
    list_receipt_files,
    move_drive_item_to_processed,
    move_drive_item_to_review,
)


class InboxResult(str, Enum):
    PROCESSED = "processed"
    REVIEW = "review"
    FAILED = "failed"


def process_receipt(item: dict) -> InboxResult:
    filename = item["name"]
    item_id = item["id"]

    print()
    print(f"Processing OneDrive receipt: {filename}")

    try:
        content = download_drive_item(item_id)

        # Preserve the original filename while keeping the downloaded
        # file isolated from local receipt storage.
        with tempfile.TemporaryDirectory(
            prefix="receipt-project-"
        ) as temp_dir:
            local_path = Path(temp_dir) / filename
            local_path.write_bytes(content)

            status = ingest_receipt(local_path)

        if status == IngestStatus.REVIEW_REQUIRED:
            moved = move_drive_item_to_review(
                item_id=item_id,
                original_filename=filename,
            )

            print(
                "Moved to review:",
                moved.get("name", filename),
            )

            return InboxResult.REVIEW

        if status in {
            IngestStatus.INSERTED,
            IngestStatus.DUPLICATE,
        }:
            moved = move_drive_item_to_processed(
                item_id=item_id,
                original_filename=filename,
            )

            print(
                "Moved to processed:",
                moved.get("name", filename),
            )

            return InboxResult.PROCESSED

        raise RuntimeError(
            f"Unexpected ingestion status: {status}"
        )

    except Exception as exc:
        print(
            f"Processing FAILED for {filename}: {exc}"
        )
        print(
            "File remains in /Receipts for retry."
        )

        return InboxResult.FAILED


def main():
    files = list_receipt_files()

    print(f"Receipt candidates found: {len(files)}")

    if not files:
        print("Nothing to process.")
        return

    processed = 0
    review = 0
    failed = 0

    for item in files:
        result = process_receipt(item)

        if result == InboxResult.PROCESSED:
            processed += 1

        elif result == InboxResult.REVIEW:
            review += 1

        else:
            failed += 1

    print()
    print("OneDrive inbox processing complete.")
    print(f"Processed: {processed}")
    print(f"Needs review: {review}")
    print(f"Failed: {failed}")

    # Review-required receipts have been safely quarantined and are
    # therefore not considered an orchestration failure.
    #
    # Transient/unexpected failures stay in /Receipts and make the
    # workflow fail so the problem is visible.
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()