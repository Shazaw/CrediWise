"""`parse_pdf` golden tests (PLAN §15.3 item 2, FR-4 AC1-AC3; §21.1 gate tests).

Fixtures are synthesized in-process via `tests/support/pdf_builder.py` — no
checked-in binaries (CLAUDE.md §15.1).
"""

from decimal import Decimal

from tests.support.pdf_builder import bca_style_statement_lines, build_pdf

from app.engines.extraction.pdf_parser import parse_pdf
from app.engines.extraction.schema import ExtractionStatus, RowDirection


def test_clean_bca_statement_extracts_all_rows() -> None:
    data = build_pdf(bca_style_statement_lines())

    result = parse_pdf(data)

    assert result.status is ExtractionStatus.EXTRACTED
    assert result.format_name == "BCA_STYLE_DIGITAL_V1"
    assert result.format_detection_confidence == Decimal("1.0")
    assert len(result.rows) == 5
    assert result.detected_account_holder_name == "BUDI SANTOSO"
    assert result.statement_start_date is not None
    assert result.statement_start_date.isoformat() == "2026-06-01"
    assert result.statement_end_date is not None
    assert result.statement_end_date.isoformat() == "2026-06-30"


def test_row_fields_are_parsed_correctly() -> None:
    data = build_pdf(bca_style_statement_lines())

    result = parse_pdf(data)

    salary_row = result.rows[1]
    assert salary_row.transaction_date.isoformat() == "2026-06-02"
    assert salary_row.transaction_time is not None
    assert salary_row.transaction_time.isoformat() == "09:15:00"
    assert salary_row.raw_description == "TRSF E-BANKING CR GAJI"
    assert salary_row.amount == 2_500_000
    assert salary_row.direction is RowDirection.CREDIT
    assert salary_row.balance_after == 6_500_000
    assert salary_row.extraction_confidence == Decimal("0.98")


def test_unrecognized_layout_is_unsupported_format() -> None:
    data = build_pdf(["This is some random statement text.", "Not our fixture format at all."])

    result = parse_pdf(data)

    assert result.status is ExtractionStatus.UNSUPPORTED_FORMAT
    assert result.rows == []
    assert result.reason_code == "unrecognized_statement_layout"


def test_corrupt_pdf_bytes_is_unsupported_format() -> None:
    result = parse_pdf(b"not a pdf at all")

    assert result.status is ExtractionStatus.UNSUPPORTED_FORMAT
    assert result.reason_code == "pdf_unreadable"


def test_forensics_captures_incremental_update_markers() -> None:
    clean = build_pdf(bca_style_statement_lines())
    tampered = build_pdf(bca_style_statement_lines(), extra_eof_markers=3)

    clean_result = parse_pdf(clean)
    tampered_result = parse_pdf(tampered)

    assert clean_result.pdf_forensics is not None
    assert clean_result.pdf_forensics.incremental_update_count == 0
    assert tampered_result.pdf_forensics is not None
    assert tampered_result.pdf_forensics.incremental_update_count == 3


def test_forensics_reports_page_count_and_no_signature() -> None:
    data = build_pdf(bca_style_statement_lines())

    result = parse_pdf(data)

    assert result.pdf_forensics is not None
    assert result.pdf_forensics.page_count == 1
    assert result.pdf_forensics.has_digital_signature is False


def test_empty_row_amount_zero_is_parsed() -> None:
    data = build_pdf(bca_style_statement_lines())

    result = parse_pdf(data)

    opening_balance_row = result.rows[0]
    assert opening_balance_row.amount == 0
    assert opening_balance_row.raw_description == "Saldo Awal"
