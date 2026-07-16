"""Digital PDF extraction (PLAN §15.3 item 2, C4: "pdfplumber tables (digital)
→ rows; PyMuPDF for metadata"). One supported layout for Sprint 3 (FR-4 AC1):
the delimited BCA-style fixture in `delimited_text.py`.

**Sprint 3 gap-fill (PLAN §24.11):** metadata/structural forensics use
`pypdf` (already a dependency since Sprint 2's `file_security.py`) instead
of PyMuPDF — `pypdf.DocumentInformation` already parses `/CreationDate` and
`/ModDate` into `datetime`s, covering everything §15.3 item 3 needs
(creation/mod date, producer/creator, incremental-edit count via `%%EOF`
counting, signature presence via `/ByteRange`) without a second, much
heavier PDF library for redundant capability (CLAUDE.md §9: search existing
deps before adding new ones). Revisit only if a real fixture surfaces a
signal pypdf can't expose.

pdfplumber/pypdf parse bytes already fully resident in memory — no
filesystem, network, clock, or subprocess I/O — so, like `file_security.py`'s
Pillow/pypdf calls, this stays inside `engines/` per PLAN §10.1 Golden Rule 3.
"""

import io
from decimal import Decimal

import pdfplumber
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.engines.extraction.delimited_text import parse_delimited_lines
from app.engines.extraction.schema import ExtractionResult, ExtractionStatus, PdfForensics

PARSER_NAME = "pdfplumber_bca_style"
PARSER_VERSION = "1.0.0"
FORMAT_NAME = "BCA_STYLE_DIGITAL_V1"

# pdfplumber's own extracted text for our synthetic, non-scanned fixture is
# exact (no OCR uncertainty) — a small, fixed shortfall below 1.0 reflects
# ordinary column-alignment/whitespace risk on real-world statement layouts.
_DIGITAL_ROW_CONFIDENCE = Decimal("0.98")

_INCREMENTAL_UPDATE_MARKER = b"%%EOF"
_SIGNATURE_MARKER = b"/ByteRange"


def parse_pdf(data: bytes) -> ExtractionResult:
    forensics = _extract_forensics(data)

    all_lines: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_lines.extend(text.splitlines())
    except Exception:  # noqa: BLE001 - any pdfplumber parse failure is UNSUPPORTED_FORMAT
        return ExtractionResult(
            status=ExtractionStatus.UNSUPPORTED_FORMAT,
            format_name="UNKNOWN",
            format_detection_confidence=Decimal("0"),
            parser_name=PARSER_NAME,
            parser_version=PARSER_VERSION,
            pdf_forensics=forensics,
            reason_code="pdf_unreadable",
        )

    parsed = parse_delimited_lines(all_lines, row_confidence=_DIGITAL_ROW_CONFIDENCE)
    if not parsed.header_found:
        return ExtractionResult(
            status=ExtractionStatus.UNSUPPORTED_FORMAT,
            format_name="UNKNOWN",
            format_detection_confidence=Decimal("0"),
            parser_name=PARSER_NAME,
            parser_version=PARSER_VERSION,
            pdf_forensics=forensics,
            reason_code="unrecognized_statement_layout",
        )

    return ExtractionResult(
        status=ExtractionStatus.EXTRACTED,
        format_name=FORMAT_NAME,
        format_detection_confidence=Decimal("1.0"),
        parser_name=PARSER_NAME,
        parser_version=PARSER_VERSION,
        rows=parsed.rows,
        statement_start_date=parsed.statement_start_date,
        statement_end_date=parsed.statement_end_date,
        detected_account_holder_name=parsed.detected_account_holder_name,
        pdf_forensics=forensics,
    )


def _extract_forensics(data: bytes) -> PdfForensics | None:
    try:
        reader = PdfReader(io.BytesIO(data))
        page_count = len(reader.pages)
        info = reader.metadata
    except PdfReadError:
        return None

    fonts: set[str] = set()
    for page in reader.pages:
        resources = page.get("/Resources")
        if resources is None:
            continue
        font_dict = resources.get("/Font")
        if font_dict is None:
            continue
        for font_ref in font_dict.values():
            try:
                font_obj = font_ref.get_object()
            except Exception:  # noqa: BLE001 - a malformed font ref shouldn't abort forensics
                continue
            base_font = font_obj.get("/BaseFont")
            if base_font is not None:
                fonts.add(str(base_font))

    incremental_updates = max(0, data.count(_INCREMENTAL_UPDATE_MARKER) - 1)

    return PdfForensics(
        creation_date=info.creation_date if info else None,
        modification_date=info.modification_date if info else None,
        producer=info.producer if info else None,
        creator=info.creator if info else None,
        has_digital_signature=_SIGNATURE_MARKER in data,
        incremental_update_count=incremental_updates,
        distinct_font_count=len(fonts),
        page_count=page_count,
    )
