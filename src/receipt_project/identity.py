import hashlib
import json
from pathlib import Path

from receipt_project.models.receipt import Receipt


MIN_STRONG_TRANSACTION_ID_LENGTH = 6


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


def is_strong_transaction_id(
    transaction_id: str | None,
) -> bool:
    """
    Return True only when the extracted transaction identifier is
    strong enough to participate in logical receipt deduplication.

    Logical deduplication is intentionally conservative. A false
    negative merely means two representations of the same receipt
    may require review later. A false positive could incorrectly
    suppress a legitimate purchase.

    Short values such as Costco's "Trn: 179" are therefore not
    considered strong transaction identifiers.

    The length check counts only letters and digits so separators
    such as hyphens or spaces do not artificially make an identifier
    appear stronger.
    """
    if not transaction_id:
        return False

    normalized = "".join(
        character
        for character in transaction_id.strip()
        if character.isalnum()
    )

    return len(normalized) >= MIN_STRONG_TRANSACTION_ID_LENGTH


def calculate_receipt_fingerprint(
    receipt: Receipt,
) -> str | None:
    """
    Return a logical receipt fingerprint only when strong transaction
    identity is available.

    We deliberately do not fingerprint receipts using only date,
    total, or item descriptions because OCR/extraction errors could
    cause false duplicate matches.
    """
    if not is_strong_transaction_id(
        receipt.transaction_id
    ):
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