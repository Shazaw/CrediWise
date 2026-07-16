"""Extraction-schema deterministic duplicate signals."""

from datetime import date
from decimal import Decimal

from app.engines.extraction.schema import ExtractedRow, RowDirection, duplicate_row_flags


def test_duplicate_flags_mark_only_repeated_transaction_identity() -> None:
    row = ExtractedRow(
        transaction_date=date(2026, 6, 5),
        transaction_time=None,
        raw_description="TOKO GROSIR MAKMUR",
        amount=875_000,
        direction=RowDirection.DEBIT,
        balance_after=3_125_000,
        extraction_confidence=Decimal("0.99"),
        page=1,
    )
    distinct = ExtractedRow(
        transaction_date=row.transaction_date,
        transaction_time=row.transaction_time,
        raw_description=row.raw_description,
        amount=row.amount + 1,
        direction=row.direction,
        balance_after=row.balance_after,
        extraction_confidence=row.extraction_confidence,
        page=row.page,
    )

    assert duplicate_row_flags([row, row, distinct]) == [False, True, False]
