"""Extraction engine result types (PLAN §15.2 normalized intermediate schema; FR-4).

Pure data — no I/O, no ORM. `ExtractionService` (app/services/) maps
`ExtractedRow` onto `Transaction` rows and stamps lineage columns
(`processing_run_id`, `financial_account_id`, ...) that only the DB layer
knows about.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from datetime import time as dtime
from decimal import Decimal
from enum import StrEnum, auto


class ExtractionStatus(StrEnum):
    EXTRACTED = auto()
    UNSUPPORTED_FORMAT = auto()


class RowDirection(StrEnum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


@dataclass(frozen=True)
class ExtractedRow:
    transaction_date: date
    transaction_time: dtime | None
    raw_description: str
    amount: int
    direction: RowDirection
    balance_after: int | None
    extraction_confidence: Decimal
    page: int


@dataclass(frozen=True)
class PdfForensics:
    """Deterministic structural-forensics signals feeding `metadata_score`/
    `visual_score` (PLAN §15.3 items 3 and 6)."""

    creation_date: datetime | None
    modification_date: datetime | None
    producer: str | None
    creator: str | None
    has_digital_signature: bool
    incremental_update_count: int
    distinct_font_count: int
    page_count: int


@dataclass(frozen=True)
class ExtractionResult:
    status: ExtractionStatus
    format_name: str
    format_detection_confidence: Decimal
    parser_name: str
    parser_version: str
    rows: list[ExtractedRow] = field(default_factory=list)
    statement_start_date: date | None = None
    statement_end_date: date | None = None
    detected_account_holder_name: str | None = None
    pdf_forensics: PdfForensics | None = None
    reason_code: str | None = None


def duplicate_row_flags(rows: list[ExtractedRow]) -> list[bool]:
    """Mark each repeated transaction identity after its first occurrence."""
    seen: set[tuple[date, int, str, RowDirection]] = set()
    flags: list[bool] = []
    for row in rows:
        key = (row.transaction_date, row.amount, row.raw_description, row.direction)
        flags.append(key in seen)
        seen.add(key)
    return flags
