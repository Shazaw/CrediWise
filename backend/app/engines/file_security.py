"""File-security stage (PLAN §7.2, FR-3; pure per §10.1 — no DB/network/clock).

Given the raw uploaded bytes plus the declared MIME type and (for PDFs) an
optional password, deterministically decides whether the file may proceed
into the pipeline. This is the entire FR-3 AC1-AC5 validation surface:
size cap, declared-vs-magic-byte MIME cross-check, PDF password/decrypt,
suspicious-PDF-action scan, and image decompression-bomb/pixel caps.

Why this runs synchronously ahead of the Celery `documents` queue (rather
than inside the `process_document` worker task, as PLAN §8.2's diagram might
suggest) is explained in `app/services/document_service.py` and ADR-013:
password material must never cross the Celery/Redis boundary (PLAN §24.10),
and dedup must gate the HTTP response before any row is created (FR-3 AC3).
"""

import io
from dataclasses import dataclass
from enum import StrEnum, auto

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

from app.core.errors import (
    InvalidPdfPasswordError,
    PdfPasswordRequiredError,
    UnsupportedMediaTypeError,
)

_SUPPORTED_MIME_TYPES = frozenset({"application/pdf", "text/csv", "image/png", "image/jpeg"})

# Deterministic magic-byte signatures (PLAN FR-3 AC5). CSV has no reliable
# signature — it is validated by decodability instead (see `_check_csv`).
_PDF_MAGIC = b"%PDF-"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"

# Object-graph keys that indicate an executable/embedded PDF action (PLAN
# §18.6 "malicious file" threat; the same string-key technique used by
# well-known PDF forensics tools such as Didier Stevens's `pdfid.py`).
_SUSPICIOUS_PDF_KEYS = frozenset(
    {"/JS", "/JavaScript", "/OpenAction", "/AA", "/Launch", "/EmbeddedFile"}
)
_MAX_SCAN_NODES = 5_000


class SecurityOutcome(StrEnum):
    PASSED = auto()
    REJECTED_SECURITY = auto()
    VALIDATION_FAILED = auto()


@dataclass(frozen=True)
class FileSecurityConfig:
    max_upload_bytes: int
    max_pdf_pages: int
    max_image_pixels: int


@dataclass(frozen=True)
class FileSecurityResult:
    outcome: SecurityOutcome
    reason_code: str
    detected_mime: str
    page_count: int | None = None


def validate(
    data: bytes,
    *,
    declared_content_type: str,
    password: str | None,
    config: FileSecurityConfig,
) -> FileSecurityResult:
    """FR-3 AC1-AC5. Raises a domain error for the two same-request "please
    retry" cases (unsupported MIME, PDF password needed/wrong) that never
    produce a stored `source_documents` row; returns a typed result for the
    outcomes that do (`PASSED`, `REJECTED_SECURITY`, `VALIDATION_FAILED`).
    """
    if declared_content_type not in _SUPPORTED_MIME_TYPES:
        raise UnsupportedMediaTypeError(
            f"Unsupported content type: {declared_content_type}",
            details={"declared_content_type": declared_content_type},
        )

    if len(data) == 0:
        return FileSecurityResult(
            SecurityOutcome.VALIDATION_FAILED, "empty_file", declared_content_type
        )
    if len(data) > config.max_upload_bytes:
        return FileSecurityResult(
            SecurityOutcome.VALIDATION_FAILED, "oversized_file", declared_content_type
        )

    detected = _sniff_mime(data)
    if detected is None:
        # CSV has no magic bytes; anything else we can't identify is corrupt.
        if declared_content_type == "text/csv":
            return _check_csv(data)
        return FileSecurityResult(
            SecurityOutcome.VALIDATION_FAILED, "corrupt_or_unreadable", declared_content_type
        )
    if detected != declared_content_type:
        return FileSecurityResult(
            SecurityOutcome.REJECTED_SECURITY, "declared_mime_mismatch", declared_content_type
        )

    if detected == "application/pdf":
        return _check_pdf(data, password=password, config=config)
    if detected in ("image/png", "image/jpeg"):
        return _check_image(data, config=config)
    return _check_csv(data)  # pragma: no cover — unreachable, detected is one of the above


def _sniff_mime(data: bytes) -> str | None:
    if data.startswith(_PDF_MAGIC):
        return "application/pdf"
    if data.startswith(_PNG_MAGIC):
        return "image/png"
    if data.startswith(_JPEG_MAGIC):
        return "image/jpeg"
    return None


def _check_csv(data: bytes) -> FileSecurityResult:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return FileSecurityResult(SecurityOutcome.VALIDATION_FAILED, "not_utf8_text", "text/csv")
    return FileSecurityResult(SecurityOutcome.PASSED, "passed", "text/csv")


def _check_pdf(
    data: bytes, *, password: str | None, config: FileSecurityConfig
) -> FileSecurityResult:
    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError:
        return FileSecurityResult(
            SecurityOutcome.VALIDATION_FAILED, "corrupt_or_unreadable", "application/pdf"
        )

    if reader.is_encrypted:
        if password is None:
            raise PdfPasswordRequiredError("This PDF is password-protected")
        if reader.decrypt(password) == 0:
            raise InvalidPdfPasswordError("The supplied PDF password is incorrect")

    try:
        page_count = len(reader.pages)
    except PdfReadError:
        return FileSecurityResult(
            SecurityOutcome.VALIDATION_FAILED, "corrupt_or_unreadable", "application/pdf"
        )

    if page_count > config.max_pdf_pages:
        return FileSecurityResult(
            SecurityOutcome.VALIDATION_FAILED, "too_many_pages", "application/pdf", page_count
        )

    suspicious = _scan_for_suspicious_actions(reader)
    if suspicious is not None:
        return FileSecurityResult(
            SecurityOutcome.REJECTED_SECURITY, suspicious, "application/pdf", page_count
        )

    return FileSecurityResult(SecurityOutcome.PASSED, "passed", "application/pdf", page_count)


def _scan_for_suspicious_actions(reader: PdfReader) -> str | None:
    """Bounded walk of the (already-decrypted, if applicable) object graph
    starting from the trailer, looking for executable/embedded-content keys.
    A `seen` set of object ids guards against circular indirect references.
    """
    seen: set[tuple[int, int]] = set()
    stack: list[object] = [reader.trailer]
    visited_nodes = 0

    while stack and visited_nodes < _MAX_SCAN_NODES:
        node = stack.pop()
        visited_nodes += 1

        if isinstance(node, IndirectObject):
            key = (node.idnum, node.generation)
            if key in seen:
                continue
            seen.add(key)
            try:
                stack.append(node.get_object())
            except Exception:  # noqa: BLE001 - a malformed indirect ref is not fatal to the scan
                continue
        elif isinstance(node, DictionaryObject):
            for dict_key, value in node.items():
                if str(dict_key) in _SUSPICIOUS_PDF_KEYS:
                    return f"suspicious_pdf_action_detected:{str(dict_key).lstrip('/')}"
                stack.append(value)
        elif isinstance(node, ArrayObject):
            stack.extend(node)

    return None


def _check_image(data: bytes, *, config: FileSecurityConfig) -> FileSecurityResult:
    try:
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            if width * height > config.max_image_pixels:
                return FileSecurityResult(
                    SecurityOutcome.VALIDATION_FAILED,
                    "decompression_bomb_suspected",
                    img.format or "",
                )
            img.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return FileSecurityResult(
            SecurityOutcome.VALIDATION_FAILED, "corrupt_or_unreadable", "image"
        )

    detected_mime = "image/png" if data.startswith(_PNG_MAGIC) else "image/jpeg"
    return FileSecurityResult(SecurityOutcome.PASSED, "passed", detected_mime)
