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


def get_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file."
        )

    return api_key


def generate_receipt(
    file_path: Path,
    prompt: str,
) -> Receipt:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Receipt file not found: {file_path}"
        )

    client = create_client(get_api_key())

    file_bytes = file_path.read_bytes()
    mime_type = get_mime_type(file_path)

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


def extract_receipt(file_path: Path) -> Receipt:
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

6. A quantity/unit-price helper line may appear immediately before OR
   immediately after the merchandise line it describes.

7. Do not automatically associate a quantity helper line with the previous
   merchandise item merely because it appears after that item.

8. Use the printed merchandise total and arithmetic to determine which item
   a quantity helper line belongs to.

   Example:

       PRODUCT A 11.99
       2 @ 3.06
       PRODUCT B 6.12

   should normally mean:

       PRODUCT A:
           quantity = 1
           unit_price = 11.99
           total_price = 11.99

       PRODUCT B:
           quantity = 2
           unit_price = 3.06
           total_price = 6.12

   because 2 * 3.06 = 6.12.

9. When a quantity helper line can be matched to an item through exact
   arithmetic, prefer that interpretation over positional assumptions.

10. Do NOT interpret trailing store codes, tax codes, category codes,
    letters such as E/Y, or standalone digits printed after a price as
    quantity.

11. For Costco receipts specifically, trailing values such as "3" or "Y"
    after an item price are not quantities unless the receipt explicitly
    identifies them as such.

12. unit_price should be populated only when a separate per-unit price can
    actually be determined from the receipt.

13. If quantity is 1 and only one line price is shown, that line price may
    also be used as unit_price.

14. total_price is the merchandise line amount before any separately
    printed coupon or discount line.

15. Extract coupons, instant savings, and other negative adjustment lines
    into discounts.

16. Store discount amount as a positive number.

17. If a discount references an item number, populate related_item_code
    when identifiable.

18. Do not put discounts into items.

19. Do not include subtotal, tax, total, tender, membership numbers,
    barcodes, payment information, or store metadata as purchased items.

20. If tax is not shown, use null.

21. If subtotal is not shown, use null.

22. Never invent unreadable values.

23. source_file must be exactly:
    {file_path.name}

24. Separate store item/SKU numbers from product descriptions.

25. Put the item/SKU number in store_item_code.

26. Do not include store_item_code again in raw_description.

27. Extract the strongest clearly printed store transaction or receipt
    identifier into transaction_id.

28. Do not invent a transaction_id.

29. Prefer a full transaction or receipt identifier over short register,
    terminal, operator, sequence, lane, or store metadata values.

30. For Costco receipts specifically:

    - A long transaction identifier may appear next to the transaction
      date/time and may be printed more than once.
    - Use that long identifier as transaction_id when clearly visible.
    - Do NOT use the short value labeled "Trn:" as transaction_id when
      a longer transaction identifier is present.
    - Values labeled "Whse:", "Trm:", "Trn:", and "OPT:" are store,
      terminal, transaction-sequence, or operator metadata and should
      not be preferred over the full transaction identifier.

31. If no sufficiently clear transaction or receipt identifier is visible,
    set transaction_id to null rather than guessing.

32. If the purchase date is not clearly visible in the supplied file,
    set purchase_date to null. Never infer, estimate, or guess the
    purchase date from other information.
"""

    return generate_receipt(
        file_path=file_path,
        prompt=prompt,
    )


def repair_receipt_extraction(
    file_path: Path,
    receipt: Receipt,
    validation_issues: list[str],
) -> Receipt:
    issues_text = "\n".join(
        f"- {issue}"
        for issue in validation_issues
    )

    existing_json = receipt.model_dump_json(
        indent=2,
    )

    prompt = f"""
Re-read this receipt and repair the structured extraction below.

The first extraction failed arithmetic validation.

Validation problems:

{issues_text}

Current structured extraction:

{existing_json}

Return the complete corrected receipt structure.

Important repair rules:

1. Use the original receipt as the source of truth.

2. Do not change values merely to force the arithmetic to balance.

3. Re-read every merchandise line, quantity helper line, coupon,
   subtotal, tax, and total from the receipt.

4. Pay particular attention to quantity helper lines such as:

       2 @ 3.06

   Such a helper line may belong to the merchandise line immediately
   following it rather than the merchandise line before it.

5. Match quantity helper lines using arithmetic.

   Example:

       PRODUCT A 11.99
       2 @ 3.06
       PRODUCT B 6.12

   means:

       PRODUCT A:
           quantity = 1
           unit_price = 11.99
           total_price = 11.99

       PRODUCT B:
           quantity = 2
           unit_price = 3.06
           total_price = 6.12

   because 2 * 3.06 = 6.12.

6. Preserve printed merchandise amounts before separately printed
   discounts.

7. Do not invent missing prices or quantities.

8. Keep discounts separate from merchandise items.

9. source_file must remain exactly:

   {file_path.name}

10. Return the complete receipt, not only the fields that changed.
"""

    return generate_receipt(
        file_path=file_path,
        prompt=prompt,
    )