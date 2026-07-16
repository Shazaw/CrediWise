"""`parse_csv` golden tests (PLAN FR-3 AC1 `text/csv`, FR-4 AC1; §21.1 gate tests)."""

from decimal import Decimal

from app.engines.extraction.csv_parser import parse_csv
from app.engines.extraction.schema import ExtractionStatus, RowDirection

_CLEAN_CSV = (
    b"CREDIWISE BANK STATEMENT\n"
    b"Nama: BUDI SANTOSO\n"
    b"Periode: 01/06/2026 - 30/06/2026\n"
    b"\n"
    b"Tanggal,Waktu,Keterangan,Tipe,Jumlah,Saldo\n"
    b"01/06/2026,08:00,Saldo Awal,CR,0,4000000\n"
    b"02/06/2026,09:15,TRSF E-BANKING CR GAJI,CR,2500000,6500000\n"
)


def test_clean_csv_extracts_all_rows() -> None:
    result = parse_csv(_CLEAN_CSV)

    assert result.status is ExtractionStatus.EXTRACTED
    assert result.format_name == "EXPORTED_CSV_V1"
    assert len(result.rows) == 2
    assert result.detected_account_holder_name == "BUDI SANTOSO"

    salary_row = result.rows[1]
    assert salary_row.amount == 2_500_000
    assert salary_row.direction is RowDirection.CREDIT
    assert salary_row.extraction_confidence == Decimal("1.0")


def test_non_utf8_bytes_is_unsupported_format() -> None:
    result = parse_csv(b"\xff\xfe\x00\x01not utf-8")

    assert result.status is ExtractionStatus.UNSUPPORTED_FORMAT
    assert result.reason_code == "not_utf8_text"


def test_unrecognized_csv_layout_is_unsupported_format() -> None:
    result = parse_csv(b"col_a,col_b,col_c\n1,2,3\n")

    assert result.status is ExtractionStatus.UNSUPPORTED_FORMAT
    assert result.reason_code == "unrecognized_statement_layout"
