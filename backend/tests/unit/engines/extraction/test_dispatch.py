"""`extract()` MIME-type dispatch (PLAN §15.1)."""

from tests.support.pdf_builder import bca_style_statement_lines, build_pdf

from app.engines.extraction import extract
from app.engines.extraction.schema import ExtractionStatus


def test_dispatches_pdf_to_pdf_parser() -> None:
    result = extract(
        build_pdf(bca_style_statement_lines()), mime_type="application/pdf", ocr_text=None
    )

    assert result.status is ExtractionStatus.EXTRACTED
    assert result.format_name == "BCA_STYLE_DIGITAL_V1"


def test_image_without_ocr_text_is_unsupported() -> None:
    result = extract(b"fake-image-bytes", mime_type="image/png", ocr_text=None)

    assert result.status is ExtractionStatus.UNSUPPORTED_FORMAT
    assert result.reason_code == "ocr_unavailable"


def test_image_with_ocr_text_dispatches_to_image_parser() -> None:
    text = "\n".join(bca_style_statement_lines())

    result = extract(b"fake-image-bytes", mime_type="image/jpeg", ocr_text=text)

    assert result.status is ExtractionStatus.EXTRACTED
    assert result.format_name == "GOPAY_STYLE_SCREENSHOT_V1"


def test_unknown_mime_type_is_unsupported() -> None:
    result = extract(b"...", mime_type="application/octet-stream", ocr_text=None)

    assert result.status is ExtractionStatus.UNSUPPORTED_FORMAT
    assert result.reason_code == "unsupported_mime_type"
