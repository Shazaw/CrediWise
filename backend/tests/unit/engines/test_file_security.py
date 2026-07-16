"""`FileSecurityEngine` golden tests (PLAN §7.2, FR-3 AC1-AC5; §21.1 gate tests).

All fixtures are synthesized in-process (no checked-in binaries) — CrediWise
never stores real financial documents, and synthetic fixtures keep this test
deterministic and reviewable (CLAUDE.md §15.1).
"""

import io

import pytest
from PIL import Image
from pypdf import PdfWriter

from app.core.errors import (
    InvalidPdfPasswordError,
    PdfPasswordRequiredError,
    UnsupportedMediaTypeError,
)
from app.engines.file_security import FileSecurityConfig, SecurityOutcome, validate

_CONFIG = FileSecurityConfig(
    max_upload_bytes=15 * 1024 * 1024, max_pdf_pages=60, max_image_pixels=25_000_000
)


def _clean_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _malicious_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_js('app.alert("hi");')
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _encrypted_pdf_bytes(password: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt(user_password=password, owner_password=None)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _png_bytes(width: int = 10, height: int = 10) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color="red").save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(width: int = 10, height: int = 10) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color="blue").save(buf, format="JPEG")
    return buf.getvalue()


def test_clean_pdf_passes() -> None:
    result = validate(
        _clean_pdf_bytes(), declared_content_type="application/pdf", password=None, config=_CONFIG
    )
    assert result.outcome is SecurityOutcome.PASSED
    assert result.page_count == 1


def test_clean_csv_passes() -> None:
    result = validate(
        b"date,amount\n2026-01-01,1000\n",
        declared_content_type="text/csv",
        password=None,
        config=_CONFIG,
    )
    assert result.outcome is SecurityOutcome.PASSED


def test_clean_png_passes() -> None:
    result = validate(
        _png_bytes(), declared_content_type="image/png", password=None, config=_CONFIG
    )
    assert result.outcome is SecurityOutcome.PASSED


def test_clean_jpeg_passes() -> None:
    result = validate(
        _jpeg_bytes(), declared_content_type="image/jpeg", password=None, config=_CONFIG
    )
    assert result.outcome is SecurityOutcome.PASSED


def test_unsupported_declared_mime_raises() -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        validate(
            b"whatever", declared_content_type="application/exe", password=None, config=_CONFIG
        )


def test_empty_file_is_validation_failed() -> None:
    result = validate(b"", declared_content_type="application/pdf", password=None, config=_CONFIG)
    assert result.outcome is SecurityOutcome.VALIDATION_FAILED
    assert result.reason_code == "empty_file"


def test_oversized_file_is_validation_failed() -> None:
    tiny_config = FileSecurityConfig(
        max_upload_bytes=10, max_pdf_pages=60, max_image_pixels=25_000_000
    )
    result = validate(
        _clean_pdf_bytes(),
        declared_content_type="application/pdf",
        password=None,
        config=tiny_config,
    )
    assert result.outcome is SecurityOutcome.VALIDATION_FAILED
    assert result.reason_code == "oversized_file"


def test_corrupt_pdf_is_validation_failed() -> None:
    result = validate(
        b"%PDF-1.4 not actually a real pdf structure",
        declared_content_type="application/pdf",
        password=None,
        config=_CONFIG,
    )
    assert result.outcome is SecurityOutcome.VALIDATION_FAILED
    assert result.reason_code == "corrupt_or_unreadable"


def test_declared_mime_mismatch_is_rejected_security() -> None:
    result = validate(
        _clean_pdf_bytes(), declared_content_type="image/png", password=None, config=_CONFIG
    )
    assert result.outcome is SecurityOutcome.REJECTED_SECURITY
    assert result.reason_code == "declared_mime_mismatch"


def test_pdf_with_javascript_action_is_rejected_security() -> None:
    result = validate(
        _malicious_pdf_bytes(),
        declared_content_type="application/pdf",
        password=None,
        config=_CONFIG,
    )
    assert result.outcome is SecurityOutcome.REJECTED_SECURITY
    assert "suspicious_pdf_action_detected" in result.reason_code


def test_pdf_exceeding_page_cap_is_validation_failed() -> None:
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=50, height=50)
    buf = io.BytesIO()
    writer.write(buf)
    tiny_pages_config = FileSecurityConfig(
        max_upload_bytes=15 * 1024 * 1024, max_pdf_pages=2, max_image_pixels=25_000_000
    )

    result = validate(
        buf.getvalue(),
        declared_content_type="application/pdf",
        password=None,
        config=tiny_pages_config,
    )

    assert result.outcome is SecurityOutcome.VALIDATION_FAILED
    assert result.reason_code == "too_many_pages"


def test_encrypted_pdf_without_password_prompts() -> None:
    with pytest.raises(PdfPasswordRequiredError):
        validate(
            _encrypted_pdf_bytes("correct-horse"),
            declared_content_type="application/pdf",
            password=None,
            config=_CONFIG,
        )


def test_encrypted_pdf_with_wrong_password_raises() -> None:
    with pytest.raises(InvalidPdfPasswordError):
        validate(
            _encrypted_pdf_bytes("correct-horse"),
            declared_content_type="application/pdf",
            password="wrong-password",
            config=_CONFIG,
        )


def test_encrypted_pdf_with_correct_password_passes() -> None:
    result = validate(
        _encrypted_pdf_bytes("correct-horse"),
        declared_content_type="application/pdf",
        password="correct-horse",
        config=_CONFIG,
    )
    assert result.outcome is SecurityOutcome.PASSED


def test_image_exceeding_pixel_cap_is_validation_failed() -> None:
    tiny_pixels_config = FileSecurityConfig(
        max_upload_bytes=15 * 1024 * 1024, max_pdf_pages=60, max_image_pixels=50
    )

    result = validate(
        _png_bytes(width=20, height=20),
        declared_content_type="image/png",
        password=None,
        config=tiny_pixels_config,
    )

    assert result.outcome is SecurityOutcome.VALIDATION_FAILED
    assert result.reason_code == "decompression_bomb_suspected"


def test_corrupt_image_is_validation_failed() -> None:
    truncated = _png_bytes()[:20]
    result = validate(truncated, declared_content_type="image/png", password=None, config=_CONFIG)
    assert result.outcome is SecurityOutcome.VALIDATION_FAILED


def test_not_utf8_csv_is_validation_failed() -> None:
    result = validate(
        b"\xff\xfe\x00\x01binary garbage",
        declared_content_type="text/csv",
        password=None,
        config=_CONFIG,
    )
    assert result.outcome is SecurityOutcome.VALIDATION_FAILED
    assert result.reason_code == "not_utf8_text"
