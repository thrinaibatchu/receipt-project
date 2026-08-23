import subprocess
import sys
import tempfile
from pathlib import Path

from receipt_project.onedrive import (
    download_drive_item,
    list_receipt_files,
    move_drive_item_to_processed,
)


def process_receipt(item: dict) -> bool:
    filename = item["name"]
    item_id = item["id"]

    print()
    print(f"Processing OneDrive receipt: {filename}")

    content = download_drive_item(item_id)

    # Use an isolated temporary directory while preserving the original
    # filename. That keeps receipt.source_file meaningful while avoiding
    # collisions with files already under data/raw_receipts/.
    with tempfile.TemporaryDirectory(
        prefix="receipt-project-"
    ) as temp_dir:
        local_path = Path(temp_dir) / filename
        local_path.write_bytes(content)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "receipt_project.ingest",
                str(local_path),
            ],
            check=False,
        )

    if result.returncode != 0:
        print(
            f"Ingestion FAILED for {filename}. "
            "File remains in /Receipts."
        )
        return False

    moved = move_drive_item_to_processed(
        item_id=item_id,
        original_filename=filename,
    )

    print(
        "Moved to processed:",
        moved.get("name", filename),
    )

    return True


def main():
    files = list_receipt_files()

    print(f"Receipt candidates found: {len(files)}")

    if not files:
        print("Nothing to process.")
        return

    succeeded = 0
    failed = 0

    for item in files:
        if process_receipt(item):
            succeeded += 1
        else:
            failed += 1

    print()
    print("OneDrive inbox processing complete.")
    print(f"Succeeded: {succeeded}")
    print(f"Failed: {failed}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
