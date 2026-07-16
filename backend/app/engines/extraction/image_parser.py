"""OCR-recognized-text extraction (PLAN FR-4 AC1 image/screenshot fallback).

Takes text already produced by the `OcrPort` integration (§10.1 Golden Rule
3 — the OCR subprocess call itself lives outside `engines/`, see
`app/integrations/ocr/`). Reuses the same delimited-row grammar as the
digital-PDF/CSV parsers (documented Sprint 3 simplification, see
`delimited_text.py`'s module docstring) but at a materially lower
`extraction_confidence`, reflecting real OCR recognition error.
"""

from decimal import Decimal

from app.engines.extraction.delimited_text import parse_delimited_lines
from app.engines.extraction.schema import ExtractionResult, ExtractionStatus

PARSER_NAME = "ocr_delimited"
PARSER_VERSION = "1.0.0"
FORMAT_NAME = "GOPAY_STYLE_SCREENSHOT_V1"

# Tesseract on a clean screenshot typically reports high-80s/low-90s mean
# word confidence; 0.75 is a conservative fixed default until per-word
# confidence is threaded through from `image_to_data` (tracked as a
# follow-up, not needed for the Sprint 3 exit criterion).
_OCR_ROW_CONFIDENCE = Decimal("0.75")


def parse_ocr_text(text: str) -> ExtractionResult:
    lines = text.splitlines()
    parsed = parse_delimited_lines(lines, row_confidence=_OCR_ROW_CONFIDENCE)
    if not parsed.header_found:
        return ExtractionResult(
            status=ExtractionStatus.UNSUPPORTED_FORMAT,
            format_name="UNKNOWN",
            format_detection_confidence=Decimal("0"),
            parser_name=PARSER_NAME,
            parser_version=PARSER_VERSION,
            reason_code="unrecognized_statement_layout",
        )

    return ExtractionResult(
        status=ExtractionStatus.EXTRACTED,
        format_name=FORMAT_NAME,
        format_detection_confidence=Decimal("0.9"),
        parser_name=PARSER_NAME,
        parser_version=PARSER_VERSION,
        rows=parsed.rows,
        statement_start_date=parsed.statement_start_date,
        statement_end_date=parsed.statement_end_date,
        detected_account_holder_name=parsed.detected_account_holder_name,
    )
