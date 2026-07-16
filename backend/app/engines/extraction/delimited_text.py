"""Shared line-based parser for the two Sprint 3 MVP fixture layouts (FR-4 AC1).

PLAN §15.3 item 2 splits extraction by *source*, not by exact statement
vocabulary — real bank/e-wallet exports vary, but Sprint 3 explicitly scopes
to "1-2 fixture formats... mark others UNSUPPORTED_FORMAT" (§25 Sprint 3
Risks). Both the digital-PDF fixture (`pdf_parser.py`, text extracted
in-process by pdfplumber) and the OCR-recognized text from an image fixture
(`image_parser.py`, text supplied by the `OcrPort` integration) resolve to
plain text lines and share this one delimited-row grammar — a documented
Sprint 3 simplification, not a claim that real GoPay exports look like this.

Row grammar (`|`-delimited, header row required for format detection):
    Tanggal|Waktu|Keterangan|Tipe|Jumlah|Saldo
    02/06/2026|09:15|TRSF E-BANKING CR GAJI|CR|2500000|6500000

`Waktu` may be blank. `Tipe` is `CR` (credit) or `DB` (debit). `Jumlah`/
`Saldo` are whole-rupiah integers, comma thousands-separators tolerated.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from datetime import time as dtime
from decimal import Decimal

from app.engines.extraction.schema import ExtractedRow, RowDirection

HEADER_ROW = "Tanggal|Waktu|Keterangan|Tipe|Jumlah|Saldo"

_NAME_RE = re.compile(r"^Nama\s*:\s*(.+)$", re.IGNORECASE)
_PERIOD_RE = re.compile(
    r"^Periode\s*:\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})$", re.IGNORECASE
)
_ROW_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\|(\d{2}:\d{2})?\|(.*)\|(CR|DB)\|(-?[\d,]+)\|(-?[\d,]+)$"
)
_DIRECTION_MAP = {"CR": RowDirection.CREDIT, "DB": RowDirection.DEBIT}


@dataclass(frozen=True)
class DelimitedParseResult:
    header_found: bool
    rows: list[ExtractedRow]
    detected_account_holder_name: str | None
    statement_start_date: date | None
    statement_end_date: date | None


def parse_delimited_lines(
    lines: list[str], *, row_confidence: Decimal, page_number: int = 1
) -> DelimitedParseResult:
    detected_name: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    rows: list[ExtractedRow] = []
    in_table = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if not in_table:
            name_match = _NAME_RE.match(line)
            if name_match:
                detected_name = name_match.group(1).strip()
                continue
            period_match = _PERIOD_RE.match(line)
            if period_match:
                period_start = _parse_date(period_match.group(1))
                period_end = _parse_date(period_match.group(2))
                continue
            if line == HEADER_ROW:
                in_table = True
                continue
            continue

        row_match = _ROW_RE.match(line)
        if row_match is None:
            continue
        transaction_date_raw, time_raw, description, direction_raw, amount_raw, balance_raw = (
            row_match.groups()
        )
        rows.append(
            ExtractedRow(
                transaction_date=_parse_date(transaction_date_raw),
                transaction_time=_parse_time(time_raw),
                raw_description=description.strip(),
                amount=abs(_parse_amount(amount_raw)),
                direction=_DIRECTION_MAP[direction_raw],
                balance_after=_parse_amount(balance_raw),
                extraction_confidence=row_confidence,
                page=page_number,
            )
        )

    return DelimitedParseResult(
        header_found=in_table,
        rows=rows,
        detected_account_holder_name=detected_name,
        statement_start_date=period_start,
        statement_end_date=period_end,
    )


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%d/%m/%Y").date()


def _parse_time(value: str | None) -> dtime | None:
    if not value:
        return None
    return datetime.strptime(value, "%H:%M").time()


def _parse_amount(value: str) -> int:
    return int(value.replace(",", ""))
