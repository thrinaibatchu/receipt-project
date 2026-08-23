from pathlib import Path

from receipt_project.extraction.gemini import extract_receipt
from receipt_project.validation.receipt_checks import validate_receipt_totals


def main() -> None:
    file_path = Path("data/raw_receipts/receipt_002.pdf")

    print(f"Extracting receipt: {file_path}")

    receipt = extract_receipt(file_path)

    print()
    print("Extraction successful")
    print()
    print(receipt.model_dump_json(indent=2))

    print()
    print("Running quality checks...")

    issues = validate_receipt_totals(receipt)

    if issues:
        print()
        print("Receipt requires review:")

        for issue in issues:
            print(f"  - {issue}")
    else:
        print()
        print("Receipt passed all quality checks.")


if __name__ == "__main__":
    main()
