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

RETRYABLE_HTTP_STATUS_CODES = [
    408,
    429,
    500,
    502,
    503,
    504,
]


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


def create_client(api_key: str) -> genai.Client:
    """
    Create the Gemini client with an explicit bounded retry policy.

    Transient HTTP failures such as 429 and 503 are retried with
    exponential backoff by the Google GenAI SDK. Permanent failures
    are raised immediately.
    """
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=5,
                initial_delay=2.0,
                max_delay=16.0,
                exp_base=2,
                jitter=1.0,
                http_status_codes=RETRYABLE_HTTP_STATUS_CODES,
            ),
        ),
    )


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

    client = create_client(api_key)

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

20. Separate store item/SKU numbers from product descriptions.

21. Put the item/SKU number in store_item_code.

22. Do not include store_item_code again in raw_description.

    Example:
        "664635 SWISSPERS"

    becomes:

        store_item_code = "664635"
        raw_description = "SWISSPERS"

23. Extract the strongest clearly printed store transaction or receipt
    identifier into transaction_id.

24. Do not invent a transaction_id.

25. Prefer a full transaction or receipt identifier over short register,
    terminal, operator, sequence, lane, or store metadata values.

26. For Costco receipts specifically:

    - A long transaction identifier may appear next to the transaction
      date/time and may be printed more than once.
    - Use that long identifier as transaction_id when clearly visible.
    - Do NOT use the short value labeled "Trn:" as transaction_id when
      a longer transaction identifier is present.
    - Values labeled "Whse:", "Trm:", "Trn:", and "OPT:" are store,
      terminal, transaction-sequence, or operator metadata and should
      not be preferred over the full transaction identifier.

    Example:

        07/24/2026 15:52 1175000000000
        ...
        Whse: 1175 Trm: 202 Trn: 179 OPT: 702

    should produce:

        transaction_id = "1175000000000"

    not:

        transaction_id = "179"

27. If no sufficiently clear transaction or receipt identifier is visible,
    set transaction_id to null rather than guessing.

28. If the purchase date is not clearly visible in the supplied file,
    set purchase_date to null. Never infer, estimate, or guess the
    purchase date from other information.
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