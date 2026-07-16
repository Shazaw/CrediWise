"""Exported-CSV extraction (PLAN FR-3 AC1 `text/csv`; §11.3 `EXPORTED_CSV`
source type). Same header/row grammar as `delimited_text.py`, comma-separated
instead of `|`-separated; each row is re-joined with `|` and handed to the
shared parser so both formats share one grammar/date/amount implementation.
"""

import csv
import io
from decimal import Decimal

from app.engines.extraction.delimited_text import parse_delimited_lines
from app.engines.extraction.schema import ExtractionResult, ExtractionStatus

PARSER_NAME = "csv_delimited"
PARSER_VERSION = "1.0.0"
FORMAT_NAME = "EXPORTED_CSV_V1"

# A structured CSV export carries no OCR/column-alignment uncertainty at all.
_CSV_ROW_CONFIDENCE = Decimal("1.0")


def parse_csv(data: bytes) -> ExtractionResult:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ExtractionResult(
            status=ExtractionStatus.UNSUPPORTED_FORMAT,
            format_name="UNKNOWN",
            format_detection_confidence=Decimal("0"),
            parser_name=PARSER_NAME,
            parser_version=PARSER_VERSION,
            reason_code="not_utf8_text",
        )

    lines = ["|".join(row) for row in csv.reader(io.StringIO(text))]
    parsed = parse_delimited_lines(lines, row_confidence=_CSV_ROW_CONFIDENCE)
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
        format_detection_confidence=Decimal("1.0"),
        parser_name=PARSER_NAME,
        parser_version=PARSER_VERSION,
        rows=parsed.rows,
        statement_start_date=parsed.statement_start_date,
        statement_end_date=parsed.statement_end_date,
        detected_account_holder_name=parsed.detected_account_holder_name,
    )
