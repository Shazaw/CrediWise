"""Extraction engine dispatcher (PLAN §15.1 engine inventory; FR-4).

Routes by MIME type to the format-specific parser. Image MIME types require
the caller to already have OCR-recognized text (fetched via `OcrPort` in the
service layer, PLAN §10.1 Golden Rule 3) — this module performs no I/O.
"""

from decimal import Decimal

from app.engines.extraction.csv_parser import parse_csv
from app.engines.extraction.image_parser import PARSER_NAME as _IMAGE_PARSER_NAME
from app.engines.extraction.image_parser import PARSER_VERSION as _IMAGE_PARSER_VERSION
from app.engines.extraction.image_parser import parse_ocr_text
from app.engines.extraction.pdf_parser import parse_pdf
from app.engines.extraction.schema import ExtractedRow, ExtractionResult, ExtractionStatus

__all__ = ["ExtractedRow", "ExtractionResult", "ExtractionStatus", "extract"]

_PDF_MIME = "application/pdf"
_CSV_MIME = "text/csv"
_IMAGE_MIMES = frozenset({"image/png", "image/jpeg"})


def extract(data: bytes, *, mime_type: str, ocr_text: str | None) -> ExtractionResult:
    if mime_type == _PDF_MIME:
        return parse_pdf(data)
    if mime_type == _CSV_MIME:
        return parse_csv(data)
    if mime_type in _IMAGE_MIMES:
        if ocr_text is None:
            return ExtractionResult(
                status=ExtractionStatus.UNSUPPORTED_FORMAT,
                format_name="UNKNOWN",
                format_detection_confidence=Decimal("0"),
                parser_name=_IMAGE_PARSER_NAME,
                parser_version=_IMAGE_PARSER_VERSION,
                reason_code="ocr_unavailable",
            )
        return parse_ocr_text(ocr_text)
    return ExtractionResult(
        status=ExtractionStatus.UNSUPPORTED_FORMAT,
        format_name="UNKNOWN",
        format_detection_confidence=Decimal("0"),
        parser_name="none",
        parser_version="0",
        reason_code="unsupported_mime_type",
    )
