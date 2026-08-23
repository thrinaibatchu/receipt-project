import argparse
import hashlib
import mimetypes
import subprocess
import sys
from pathlib import Path

from receipt_project.onedrive import (
    download_from_receipts,
    upload_to_receipts,
)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def main():
    parser = argparse.ArgumentParser(
        description="Test OneDrive -> local receipt ingestion bridge."
    )

    parser.add_argument(
        "receipt_path",
        type=Path,
        help="Path to an existing local receipt file.",
    )

    args = parser.parse_args()

    source_path = args.receipt_path

    if not source_path.exists():
        raise FileNotFoundError(source_path)

    original_content = source_path.read_bytes()
    original_hash = sha256_bytes(original_content)

    content_type, _ = mimetypes.guess_type(source_path.name)

    if content_type is None:
        content_type = "application/octet-stream"

    print(f"Uploading to OneDrive: {source_path.name}")

    uploaded = upload_to_receipts(
        filename=source_path.name,
        content=original_content,
        content_type=content_type,
    )

    print("Receipt upload: SUCCESS")
    print(
        "OneDrive file ID returned:",
        "YES" if uploaded.get("id") else "NO",
    )

    print(f"Downloading from OneDrive: {source_path.name}")

    downloaded_content = download_from_receipts(
        source_path.name
    )

    downloaded_hash = sha256_bytes(downloaded_content)

    if downloaded_hash != original_hash:
        raise RuntimeError(
            "SHA-256 mismatch after OneDrive round trip."
        )

    print("Receipt download: SUCCESS")
    print("SHA-256 round-trip verification: SUCCESS")

    test_filename = (
        f"_onedrive_roundtrip_{source_path.name}"
    )

    test_path = Path("data/raw_receipts") / test_filename

    test_path.write_bytes(downloaded_content)

    print()
    print(f"Passing downloaded file to ingestion: {test_path}")
    print()

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "receipt_project.ingest",
                str(test_path),
            ],
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Existing ingestion command returned "
                f"exit code {result.returncode}"
            )

    finally:
        if test_path.exists():
            test_path.unlink()

    print()
    print("OneDrive -> existing ingestion bridge: SUCCESS")


if __name__ == "__main__":
    main()
