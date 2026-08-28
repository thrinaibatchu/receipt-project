from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pypdf import PdfReader


RECORD_START_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?P<card_number>\d{12})\s+"
    r"(?P<warehouse>\d+)\s+"
    r"(?P<purchase_date>\d{1,2}/\d{1,2}/\d{4})\s+"
)

NORMAL_ROW_PATTERN = re.compile(
    r"^"
    r"(?:(?P<item_number>\d+)\s+)?"
    r"(?P<description>.+?)\s+"
    r"(?P<department>\d{1,3})\s+"
    r"(?P<register>\d{1,3})\s+"
    r"(?P<time>\d{1,4})\s+"
    r"(?P<transaction>\d{1,6})\s+"
    r"(?P<quantity>-?\d+(?:\.\d+)?)\s+"
    r"(?P<amount>-?\d+(?:\.\d+)?)"
    r"(?P<flags>(?:\s+[A-Z0-9]+){0,3})"
    r"$"
)

COUPON_ROW_PATTERN = re.compile(
    r"^"
    r"(?P<description>.+?CPN/\d+)\s+"
    r"(?P<department>\d{1,3})\s+"
    r"(?P<register>\d{1,3})\s+"
    r"(?P<transaction>\d{1,6})\s+"
    r"(?P<quantity>-?\d+(?:\.\d+)?)\s+"
    r"(?P<amount>-?\d+(?:\.\d+)?)"
    r"(?P<flags>(?:\s+[A-Z0-9]+){0,3})"
    r"$"
)

COUPON_TYPES = {
    "coupon_discount",
    "coupon_reversal",
    "coupon_adjustment",
}


@dataclass(frozen=True)
class CostcoHistoryRow:
    source_row_number: int

    card_number: str
    warehouse: str
    purchase_date: date

    item_number: str | None
    description: str

    department: str
    register: str
    transaction_number: str
    transaction_time: str | None

    quantity: Decimal
    amount: Decimal

    taxable_code: str | None
    refund_flag: str | None
    refund_receipt_flag: str | None

    row_type: str
    related_item_number: str | None

    raw_text: str

    @property
    def transaction_key(
        self,
    ) -> tuple[str, date, str, str]:
        return (
            self.warehouse,
            self.purchase_date,
            self.register,
            self.transaction_number,
        )


@dataclass(frozen=True)
class CostcoHistoryParseFailure:
    source_row_number: int
    card_number: str
    warehouse: str
    purchase_date: date
    raw_text: str
    reason: str


@dataclass(frozen=True)
class CostcoHistoryParseResult:
    rows: list[CostcoHistoryRow]
    failures: list[CostcoHistoryParseFailure]
    page_count: int
    source_record_count: int


def _clean_text(
    value: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def _parse_date(
    value: str,
) -> date:
    return datetime.strptime(
        value,
        "%m/%d/%Y",
    ).date()


def _parse_decimal(
    value: str,
) -> Decimal:
    try:
        return Decimal(value)

    except InvalidOperation as exc:
        raise ValueError(
            f"Invalid decimal value: {value}"
        ) from exc


def _parse_flags(
    raw_flags: str | None,
) -> tuple[
    str | None,
    str | None,
    str | None,
]:
    if not raw_flags:
        return None, None, None

    values = raw_flags.split()

    taxable_code = (
        values[0]
        if len(values) >= 1
        else None
    )

    refund_flag = (
        values[1]
        if len(values) >= 2
        else None
    )

    refund_receipt_flag = (
        values[2]
        if len(values) >= 3
        else None
    )

    return (
        taxable_code,
        refund_flag,
        refund_receipt_flag,
    )


def _extract_coupon_item_number(
    description: str,
) -> str | None:
    match = re.search(
        r"CPN/(?P<item_number>\d+)",
        description,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(
        "item_number"
    )


def _classify_non_coupon_row(
    *,
    quantity: Decimal,
    amount: Decimal,
) -> str:
    if (
        quantity < Decimal("0")
        or amount < Decimal("0")
    ):
        return "return"

    if quantity == Decimal("0"):
        return "adjustment"

    return "purchase"


def _classify_coupon_row(
    amount: Decimal,
) -> str:
    if amount < Decimal("0"):
        return "coupon_discount"

    if amount > Decimal("0"):
        return "coupon_reversal"

    return "coupon_adjustment"


def _parse_record_body(
    *,
    source_row_number: int,
    card_number: str,
    warehouse: str,
    purchase_date: date,
    body: str,
) -> CostcoHistoryRow:
    cleaned_body = _clean_text(
        body
    )

    coupon_match = (
        COUPON_ROW_PATTERN.match(
            cleaned_body
        )
    )

    if coupon_match:
        values = (
            coupon_match.groupdict()
        )

        quantity = _parse_decimal(
            values["quantity"]
        )

        amount = _parse_decimal(
            values["amount"]
        )

        (
            taxable_code,
            refund_flag,
            refund_receipt_flag,
        ) = _parse_flags(
            values.get("flags")
        )

        description = _clean_text(
            values["description"]
        )

        related_item_number = (
            _extract_coupon_item_number(
                description
            )
        )

        row_type = (
            _classify_coupon_row(
                amount
            )
        )

        return CostcoHistoryRow(
            source_row_number=source_row_number,
            card_number=card_number,
            warehouse=warehouse,
            purchase_date=purchase_date,
            item_number=None,
            description=description,
            department=values[
                "department"
            ],
            register=values[
                "register"
            ],
            transaction_number=values[
                "transaction"
            ],
            transaction_time=None,
            quantity=quantity,
            amount=amount,
            taxable_code=taxable_code,
            refund_flag=refund_flag,
            refund_receipt_flag=refund_receipt_flag,
            row_type=row_type,
            related_item_number=related_item_number,
            raw_text=cleaned_body,
        )

    normal_match = (
        NORMAL_ROW_PATTERN.match(
            cleaned_body
        )
    )

    if not normal_match:
        raise ValueError(
            "Row did not match a supported "
            "Costco history layout."
        )

    values = (
        normal_match.groupdict()
    )

    quantity = _parse_decimal(
        values["quantity"]
    )

    amount = _parse_decimal(
        values["amount"]
    )

    (
        taxable_code,
        refund_flag,
        refund_receipt_flag,
    ) = _parse_flags(
        values.get("flags")
    )

    description = _clean_text(
        values["description"]
    )

    row_type = (
        _classify_non_coupon_row(
            quantity=quantity,
            amount=amount,
        )
    )

    return CostcoHistoryRow(
        source_row_number=source_row_number,
        card_number=card_number,
        warehouse=warehouse,
        purchase_date=purchase_date,
        item_number=values.get(
            "item_number"
        ),
        description=description,
        department=values[
            "department"
        ],
        register=values[
            "register"
        ],
        transaction_number=values[
            "transaction"
        ],
        transaction_time=values[
            "time"
        ],
        quantity=quantity,
        amount=amount,
        taxable_code=taxable_code,
        refund_flag=refund_flag,
        refund_receipt_flag=refund_receipt_flag,
        row_type=row_type,
        related_item_number=None,
        raw_text=cleaned_body,
    )


def extract_pdf_text(
    pdf_path: Path,
) -> tuple[str, int]:
    reader = PdfReader(
        str(pdf_path)
    )

    page_texts: list[str] = []

    for page in reader.pages:
        page_text = (
            page.extract_text()
            or ""
        )

        page_texts.append(
            page_text
        )

    return (
        "\n".join(
            page_texts
        ),
        len(reader.pages),
    )


def split_source_records(
    document_text: str,
) -> list[
    tuple[
        str,
        str,
        date,
        str,
    ]
]:
    matches = list(
        RECORD_START_PATTERN.finditer(
            document_text
        )
    )

    records: list[
        tuple[
            str,
            str,
            date,
            str,
        ]
    ] = []

    for index, match in enumerate(
        matches
    ):
        body_start = match.end()

        if index + 1 < len(matches):
            body_end = matches[
                index + 1
            ].start()
        else:
            body_end = len(
                document_text
            )

        body = document_text[
            body_start:body_end
        ]

        records.append(
            (
                match.group(
                    "card_number"
                ),
                match.group(
                    "warehouse"
                ),
                _parse_date(
                    match.group(
                        "purchase_date"
                    )
                ),
                body,
            )
        )

    return records


def parse_costco_history_pdf(
    pdf_path: str | Path,
) -> CostcoHistoryParseResult:
    path = Path(
        pdf_path
    ).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            "Costco history source must be a PDF."
        )

    (
        document_text,
        page_count,
    ) = extract_pdf_text(
        path
    )

    source_records = (
        split_source_records(
            document_text
        )
    )

    rows: list[
        CostcoHistoryRow
    ] = []

    failures: list[
        CostcoHistoryParseFailure
    ] = []

    for source_row_number, (
        card_number,
        warehouse,
        purchase_date,
        body,
    ) in enumerate(
        source_records,
        start=1,
    ):
        cleaned_body = _clean_text(
            body
        )

        try:
            row = _parse_record_body(
                source_row_number=source_row_number,
                card_number=card_number,
                warehouse=warehouse,
                purchase_date=purchase_date,
                body=cleaned_body,
            )

        except ValueError as exc:
            failures.append(
                CostcoHistoryParseFailure(
                    source_row_number=source_row_number,
                    card_number=card_number,
                    warehouse=warehouse,
                    purchase_date=purchase_date,
                    raw_text=cleaned_body,
                    reason=str(exc),
                )
            )

            continue

        rows.append(
            row
        )

    return CostcoHistoryParseResult(
        rows=rows,
        failures=failures,
        page_count=page_count,
        source_record_count=len(
            source_records
        ),
    )