import os

from dotenv import load_dotenv

from receipt_project.models.receipt import Receipt


def _get_backend() -> str:
    load_dotenv()

    backend = os.getenv(
        "RECEIPT_DB_BACKEND",
        "sqlite",
    ).lower()

    if backend not in {"sqlite", "postgres"}:
        raise RuntimeError(
            "RECEIPT_DB_BACKEND must be "
            "'sqlite' or 'postgres'"
        )

    return backend


def find_receipt_by_source_hash(source_hash: str):
    if _get_backend() == "postgres":
        from receipt_project.database.postgres_writer import (
            find_receipt_by_source_hash as implementation,
        )
    else:
        from receipt_project.database.sqlite_writer import (
            find_receipt_by_source_hash as implementation,
        )

    return implementation(source_hash)


def insert_receipt(
    receipt: Receipt,
    source_hash: str,
    receipt_fingerprint: str | None,
) -> int:
    if _get_backend() == "postgres":
        from receipt_project.database.postgres_writer import (
            insert_receipt as implementation,
        )
    else:
        from receipt_project.database.sqlite_writer import (
            insert_receipt as implementation,
        )

    return implementation(
        receipt,
        source_hash,
        receipt_fingerprint,
    )
