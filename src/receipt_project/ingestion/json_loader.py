import json
from pathlib import Path

from receipt_project.models.receipt import Receipt


def load_receipt_json(file_path: Path) -> Receipt:
    with file_path.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    receipt = Receipt.model_validate(raw_data)

    return receipt
