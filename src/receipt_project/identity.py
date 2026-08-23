import hashlib
import json
from pathlib import Path

from receipt_project.models.receipt import Receipt


def calculate_source_hash(file_path: Path) -> str:
    hasher = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def normalize_store_name(store_name: str) -> str:
    return " ".join(
        store_name.strip().upper().split()
    )


def calculate_receipt_fingerprint(
    receipt: Receipt,
) -> str | None:
    """
    Return a logical receipt fingerprint only when
    strong transaction identity is available.

    We deliberately do not fingerprint receipts using
    only date, total, or item descriptions because OCR
    errors could cause false duplicate matches.
    """

    if not receipt.transaction_id:
        return None

    identity_data = {
        "store": normalize_store_name(
            receipt.store_name
        ),
        "transaction_id": (
            receipt.transaction_id.strip()
        ),
        "total": round(receipt.total, 2),
    }

    serialized = json.dumps(
        identity_data,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()