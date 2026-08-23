import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from receipt_project.models.receipt import Receipt


load_dotenv()


MODEL_NAME = "gemini-3.5-flash-lite"

SUPPORTED_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def get_mime_type(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    mime_type = SUPPORTED_MIME_TYPES.get(suffix)

    if mime_type is None:
        supported = ", ".join(SUPPORTED_MIME_TYPES.keys())

        raise ValueError(
            f"Unsupported receipt file type: {suffix}. "
            f"Supported types: {supported}"
        )

    return mime_type


def extract_receipt(file_path: Path) -> Receipt:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file."
        )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Receipt file not found: {file_path}"
        )

    client = genai.Client(api_key=api_key)

    file_bytes = file_path.read_bytes()
    mime_type = get_mime_type(file_path)

    prompt = f"""
Extract this store receipt into structured data.

The receipt may be supplied as an image or PDF.

Rules:

1. Extract only merchandise actually purchased into items.
2. Preserve each item's printed receipt description in raw_description.
3. Do not normalize or rename products.
4. quantity means the actual number of units purchased.
5. Default quantity to 1 unless the receipt explicitly shows multiple units,
   such as "2 @ 4.99", "2 x 4.99", or another clearly identified quantity.
6. Do NOT interpret trailing store codes, tax codes, category codes,
   letters such as E/Y, or standalone digits printed after a price as quantity.
7. For Costco receipts specifically, trailing values such as "3" or "Y"
   after an item price are not quantities unless the receipt explicitly
   identifies them as such.
8. unit_price should be populated only when a separate per-unit price can
   actually be determined from the receipt.
9. If quantity is 1 and only one line price is shown, that line price may
   also be used as unit_price.
10. total_price is the merchandise line amount before any separately
    printed coupon or discount line.
11. Extract coupons, instant savings, and other negative adjustment lines
    into discounts.
12. Store discount amount as a positive number.
13. If a discount references an item number, populate related_item_code
    when identifiable.
14. Do not put discounts into items.
15. Do not include subtotal, tax, total, tender, membership numbers,
    barcodes, payment information, or store metadata as purchased items.
16. If tax is not shown, use null.
17. If subtotal is not shown, use null.
18. Never invent unreadable values.
19. source_file must be exactly:
    {file_path.name}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            prompt,
            types.Part.from_bytes(
                data=file_bytes,
                mime_type=mime_type,
            ),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Receipt,
        ),
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return Receipt.model_validate_json(response.text)
