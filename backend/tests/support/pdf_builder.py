"""Synthesizes minimal, in-process PDF fixtures for extraction/Trust-Layer
tests (CLAUDE.md §15.1: "no checked-in binaries", same convention as
`tests/unit/engines/test_file_security.py`).

Builds a single-page PDF with a standard (non-embedded) Helvetica font and a
hand-written content stream drawing one left-aligned text line per row —
enough for `pdfplumber.Page.extract_text()` to read the lines back in order,
without pulling in a full PDF-generation library (PLAN §24.9: prefer what's
already a dependency).
"""

import io

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

_PAGE_WIDTH = 595
_PAGE_HEIGHT = 842
_TOP_MARGIN = 800
_LINE_HEIGHT = 14
_LEFT_MARGIN = 20
_FONT_SIZE = 10


def build_pdf(lines: list[str], *, extra_eof_markers: int = 0) -> bytes:
    """`extra_eof_markers` duplicates the trailing `startxref ... %%EOF`
    block to simulate incremental updates (PLAN §15.3 item 3/6 forensic
    signal) without hand-rolling a full incremental-save PDF structure. Each
    duplicate re-points at the same (still-valid) original xref offset — it
    doesn't add a `/Prev`-chained xref like a real incremental save, but it
    is enough for both the raw `%%EOF`-counting heuristic under test and for
    `pypdf.PdfReader` to still parse the file (bare appended `%%EOF` markers
    alone push `startxref` outside pypdf's end-of-file lookback window)."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)

    font_dict = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font_dict)  # noqa: SLF001 - low-level PDF construction
    resources = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )
    page[NameObject("/Resources")] = resources  # type: ignore[arg-type]

    content_lines = []
    y = _TOP_MARGIN
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_lines.append(f"BT /F1 {_FONT_SIZE} Tf {_LEFT_MARGIN} {y} Td ({escaped}) Tj ET")
        y -= _LINE_HEIGHT
    stream = DecodedStreamObject()
    stream.set_data("\n".join(content_lines).encode("latin-1"))
    content_ref = writer._add_object(stream)  # noqa: SLF001
    page[NameObject("/Contents")] = content_ref  # type: ignore[arg-type]

    buf = io.BytesIO()
    writer.write(buf)
    data = buf.getvalue()
    if extra_eof_markers:
        trailer_block = data[data.rfind(b"startxref") :]
        data += b"\n" + (trailer_block * extra_eof_markers)
    return data


def bca_style_statement_lines(
    *,
    holder_name: str = "BUDI SANTOSO",
    period_start: str = "01/06/2026",
    period_end: str = "30/06/2026",
    rows: list[str] | None = None,
) -> list[str]:
    default_rows = [
        "01/06/2026|08:00|Saldo Awal|CR|0|4000000",
        "02/06/2026|09:15|TRSF E-BANKING CR GAJI|CR|2500000|6500000",
        "05/06/2026|12:30|QRIS MERCHANT WARUNG SEHAT|DB|150000|6350000",
        "10/06/2026|18:45|TRANSFER KE TOKOPEDIA|DB|500000|5850000",
        "15/06/2026|09:00|TRSF E-BANKING CR GAJI|CR|2500000|8350000",
    ]
    return [
        "CREDIWISE BANK STATEMENT",
        f"Nama: {holder_name}",
        f"Periode: {period_start} - {period_end}",
        "",
        "Tanggal|Waktu|Keterangan|Tipe|Jumlah|Saldo",
        *(rows if rows is not None else default_rows),
    ]
