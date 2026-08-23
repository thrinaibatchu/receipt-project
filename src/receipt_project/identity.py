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


def calculate_receipt_fingerprint(receipt: Receipt) -> str:
    items = [
        {
            "code": item.store_item_code,
            "description": item.raw_description,
            "quantity": item.quantity,
            "total_price": item.total_price,
        }
        for item in receipt.items
    ]

    identity_data = {
        "store": receipt.store_name.strip().upper(),
        "purchase_date": receipt.purchase_date.isoformat(),
        "total": round(receipt.total, 2),
        "transaction_id": receipt.transaction_id,
        "items": items,
    }

    serialized = json.dumps(
        identity_data,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()
