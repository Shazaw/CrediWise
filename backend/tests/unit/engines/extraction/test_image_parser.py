"""`parse_ocr_text` golden tests (PLAN FR-4 AC1 image/screenshot fallback;
§21.1 gate tests). Takes already-recognized text — no real Tesseract call
(see `app/integrations/ocr/` for why OCR itself isn't in `engines/`).
"""

from decimal import Decimal

from app.engines.extraction.image_parser import parse_ocr_text
from app.engines.extraction.schema import ExtractionStatus

_OCR_TEXT = (
    "CREDIWISE BANK STATEMENT\n"
    "Nama: BUDI SANTOSO\n"
    "Periode: 01/06/2026 - 30/06/2026\n"
    "\n"
    "Tanggal|Waktu|Keterangan|Tipe|Jumlah|Saldo\n"
    "01/06/2026|08:00|Saldo Awal|CR|0|4000000\n"
    "02/06/2026|09:15|TRSF E-BANKING CR GAJI|CR|2500000|6500000\n"
)


def test_recognized_text_extracts_rows_at_lower_confidence() -> None:
    result = parse_ocr_text(_OCR_TEXT)

    assert result.status is ExtractionStatus.EXTRACTED
    assert result.format_name == "GOPAY_STYLE_SCREENSHOT_V1"
    assert len(result.rows) == 2
    assert result.rows[0].extraction_confidence == Decimal("0.75")


def test_garbled_ocr_output_is_unsupported_format() -> None:
    result = parse_ocr_text("s0me garb1ed 0cr n0ise\nwith no recognizable header")

    assert result.status is ExtractionStatus.UNSUPPORTED_FORMAT
    assert result.reason_code == "unrecognized_statement_layout"
