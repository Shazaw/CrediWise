"""`TrustLayerEngine` golden tests (PLAN §5.2, §15.3, FR-5; §21.1 gate tests,
§24.8 "engines >= 90% coverage").

Exercises the documented exit criterion (§25 Sprint 3): "clean fixture ->
HIGH confidence with reasons; tampered fixture -> lowered score with
non-accusatory explanation."
"""

from datetime import date
from datetime import time as dtime
from decimal import Decimal

from app.engines.extraction.schema import ExtractedRow, PdfForensics, RowDirection
from app.engines.trust_layer import (
    DEFAULT_CONFIG,
    KimiAnomalyEvidence,
    TrustLayerConfig,
    TrustLayerInput,
    run,
)
from app.models.enums import BandEnum, SourceTypeEnum

_ACCUSATORY_WORDS = ("fake", "fraud", "dishonest", "lying", "scam")


def _row(
    day: int,
    amount: int,
    direction: RowDirection,
    balance_after: int,
    *,
    description: str = "TRSF E-BANKING",
    confidence: str = "0.98",
) -> ExtractedRow:
    return ExtractedRow(
        transaction_date=date(2026, 6, day),
        transaction_time=dtime(9, 0),
        raw_description=description,
        amount=amount,
        direction=direction,
        balance_after=balance_after,
        extraction_confidence=Decimal(confidence),
        page=1,
    )


def _consistent_rows() -> list[ExtractedRow]:
    return [
        _row(1, 0, RowDirection.CREDIT, 4_000_000, description="Saldo Awal"),
        _row(2, 2_500_000, RowDirection.CREDIT, 6_500_000, description="TRSF E-BANKING CR GAJI"),
        _row(5, 150_000, RowDirection.DEBIT, 6_350_000, description="QRIS MERCHANT"),
        _row(10, 500_000, RowDirection.DEBIT, 5_850_000, description="TRANSFER KE TOKOPEDIA"),
        _row(15, 2_500_000, RowDirection.CREDIT, 8_350_000, description="TRSF E-BANKING CR GAJI"),
    ]


def _clean_pdf_forensics() -> PdfForensics:
    from datetime import datetime

    return PdfForensics(
        creation_date=datetime(2026, 7, 1),
        modification_date=datetime(2026, 7, 1),
        producer="CrediWise Statement Generator",
        creator="CrediWise",
        has_digital_signature=False,
        incremental_update_count=0,
        distinct_font_count=1,
        page_count=1,
    )


def test_clean_original_pdf_scores_high_with_reasons() -> None:
    inputs = TrustLayerInput(
        source_type=SourceTypeEnum.ORIGINAL_PDF,
        rows=_consistent_rows(),
        pdf_forensics=_clean_pdf_forensics(),
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 6, 30),
        declared_owner_name="Budi Santoso",
        detected_account_holder_name="BUDI SANTOSO",
    )

    result = run(inputs)

    assert result.band is BandEnum.HIGH
    assert result.data_confidence_score >= 80
    assert len(result.reason_codes) >= 3
    assert result.recommendation is None
    assert result.consistency_score == Decimal("100.00")
    assert result.ownership_score == Decimal("100")


def test_tampered_document_scores_lower_with_non_accusatory_reasons() -> None:
    tampered_forensics = PdfForensics(
        creation_date=None,
        modification_date=None,
        producer=None,
        creator=None,
        has_digital_signature=False,
        incremental_update_count=5,
        distinct_font_count=6,
        page_count=1,
    )
    rows = _consistent_rows()
    # Break the reconciliation chain and duplicate a row.
    broken_rows = [
        rows[0],
        _row(2, 2_500_000, RowDirection.CREDIT, 9_999_999, description="TRSF E-BANKING CR GAJI"),
        rows[2],
        rows[2],
    ]

    inputs = TrustLayerInput(
        source_type=SourceTypeEnum.SCREENSHOT,
        rows=broken_rows,
        pdf_forensics=tampered_forensics,
        statement_start_date=date(2026, 6, 1),
        statement_end_date=date(2026, 6, 30),
        declared_owner_name="Budi Santoso",
        detected_account_holder_name="SOMEONE ELSE ENTIRELY",
    )

    clean_result = run(
        TrustLayerInput(
            source_type=SourceTypeEnum.ORIGINAL_PDF,
            rows=_consistent_rows(),
            pdf_forensics=_clean_pdf_forensics(),
            statement_start_date=date(2026, 1, 1),
            statement_end_date=date(2026, 6, 30),
            declared_owner_name="Budi Santoso",
            detected_account_holder_name="BUDI SANTOSO",
        )
    )
    tampered_result = run(inputs)

    assert tampered_result.data_confidence_score < clean_result.data_confidence_score
    assert tampered_result.band is not BandEnum.HIGH
    assert tampered_result.recommendation is not None

    all_text = " ".join(r.description for r in tampered_result.reason_codes).lower()
    all_text += " " + (tampered_result.recommendation or "").lower()
    for banned_word in _ACCUSATORY_WORDS:
        assert banned_word not in all_text


def test_screenshot_with_no_forensics_uses_neutral_defaults() -> None:
    inputs = TrustLayerInput(
        source_type=SourceTypeEnum.SCREENSHOT,
        rows=_consistent_rows(),
        pdf_forensics=None,
        statement_start_date=date(2026, 6, 1),
        statement_end_date=date(2026, 6, 30),
        declared_owner_name="Budi Santoso",
        detected_account_holder_name="BUDI SANTOSO",
    )

    result = run(inputs)

    assert result.metadata_score == Decimal(DEFAULT_CONFIG.metadata["no_forensics_base"])
    assert result.visual_score == Decimal(DEFAULT_CONFIG.visual["no_forensics_base"])
    assert result.provenance_score == Decimal(45)  # SCREENSHOT tier


def test_no_balance_data_uses_neutral_default_not_a_penalty() -> None:
    rows = [
        ExtractedRow(
            transaction_date=date(2026, 6, 2),
            transaction_time=None,
            raw_description="TRSF",
            amount=100_000,
            direction=RowDirection.CREDIT,
            balance_after=None,
            extraction_confidence=Decimal("0.9"),
            page=1,
        )
    ]
    inputs = TrustLayerInput(
        source_type=SourceTypeEnum.EXPORTED_CSV,
        rows=rows,
        pdf_forensics=None,
        statement_start_date=None,
        statement_end_date=None,
        declared_owner_name=None,
        detected_account_holder_name=None,
    )

    result = run(inputs)

    assert result.consistency_score == Decimal(
        DEFAULT_CONFIG.consistency["no_balance_data_default"]
    )
    assert result.ownership_score == Decimal(DEFAULT_CONFIG.ownership["no_name_default"])


def test_ownership_partial_match_tolerates_titles_and_spacing() -> None:
    inputs = TrustLayerInput(
        source_type=SourceTypeEnum.ORIGINAL_PDF,
        rows=_consistent_rows(),
        pdf_forensics=_clean_pdf_forensics(),
        statement_start_date=date(2026, 6, 1),
        statement_end_date=date(2026, 6, 30),
        declared_owner_name="Budi  Santoso",
        detected_account_holder_name="Bpk. Budi Santoso",
    )

    result = run(inputs)

    assert result.ownership_score == Decimal(100)


def test_ownership_mismatch_scores_low() -> None:
    inputs = TrustLayerInput(
        source_type=SourceTypeEnum.ORIGINAL_PDF,
        rows=_consistent_rows(),
        pdf_forensics=_clean_pdf_forensics(),
        statement_start_date=date(2026, 6, 1),
        statement_end_date=date(2026, 6, 30),
        declared_owner_name="Budi Santoso",
        detected_account_holder_name="Rina Wijaya",
    )

    result = run(inputs)

    assert result.ownership_score == Decimal(DEFAULT_CONFIG.ownership["mismatch"])


def test_completeness_partial_below_target() -> None:
    inputs = TrustLayerInput(
        source_type=SourceTypeEnum.ORIGINAL_PDF,
        rows=_consistent_rows(),
        pdf_forensics=_clean_pdf_forensics(),
        statement_start_date=date(2026, 6, 1),
        statement_end_date=date(2026, 6, 30),
        declared_owner_name="Budi Santoso",
        detected_account_holder_name="Budi Santoso",
    )

    result = run(inputs)

    # 1 of 6 target months.
    assert result.completeness_score == Decimal("16.67")


def test_kimi_evidence_unavailable_sets_flag_without_penalty() -> None:
    inputs = TrustLayerInput(
        source_type=SourceTypeEnum.ORIGINAL_PDF,
        rows=_consistent_rows(),
        pdf_forensics=_clean_pdf_forensics(),
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 6, 30),
        declared_owner_name="Budi Santoso",
        detected_account_holder_name="Budi Santoso",
        kimi_evidence=KimiAnomalyEvidence(
            available=False, anomaly_probability=Decimal("0"), indicator_count=0
        ),
    )

    result = run(inputs)

    assert result.flags["ai_signal"] == "UNAVAILABLE"
    assert result.band is BandEnum.HIGH


def test_kimi_evidence_disabled_by_default_does_not_change_score() -> None:
    without_kimi = run(
        TrustLayerInput(
            source_type=SourceTypeEnum.ORIGINAL_PDF,
            rows=_consistent_rows(),
            pdf_forensics=_clean_pdf_forensics(),
            statement_start_date=date(2026, 1, 1),
            statement_end_date=date(2026, 6, 30),
            declared_owner_name="Budi Santoso",
            detected_account_holder_name="Budi Santoso",
        )
    )
    with_available_but_disabled_kimi = run(
        TrustLayerInput(
            source_type=SourceTypeEnum.ORIGINAL_PDF,
            rows=_consistent_rows(),
            pdf_forensics=_clean_pdf_forensics(),
            statement_start_date=date(2026, 1, 1),
            statement_end_date=date(2026, 6, 30),
            declared_owner_name="Budi Santoso",
            detected_account_holder_name="Budi Santoso",
            kimi_evidence=KimiAnomalyEvidence(
                available=True, anomaly_probability=Decimal("0.9"), indicator_count=3
            ),
        )
    )

    assert with_available_but_disabled_kimi.flags["ai_signal"] == "DISABLED"
    assert with_available_but_disabled_kimi.visual_score == without_kimi.visual_score


def test_kimi_evidence_included_when_enabled_lowers_visual_score() -> None:
    enabled_config = TrustLayerConfig(
        weights=DEFAULT_CONFIG.weights,
        provenance_tiers=DEFAULT_CONFIG.provenance_tiers,
        band_high_threshold=DEFAULT_CONFIG.band_high_threshold,
        band_medium_threshold=DEFAULT_CONFIG.band_medium_threshold,
        completeness_target_months=DEFAULT_CONFIG.completeness_target_months,
        metadata=DEFAULT_CONFIG.metadata,
        visual=DEFAULT_CONFIG.visual,
        consistency=DEFAULT_CONFIG.consistency,
        ownership=DEFAULT_CONFIG.ownership,
        kimi_anomaly_scoring_enabled=True,
        kimi_weight_within_visual=Decimal("0.5"),
    )
    inputs = TrustLayerInput(
        source_type=SourceTypeEnum.ORIGINAL_PDF,
        rows=_consistent_rows(),
        pdf_forensics=_clean_pdf_forensics(),
        statement_start_date=date(2026, 1, 1),
        statement_end_date=date(2026, 6, 30),
        declared_owner_name="Budi Santoso",
        detected_account_holder_name="Budi Santoso",
        kimi_evidence=KimiAnomalyEvidence(
            available=True, anomaly_probability=Decimal("0.8"), indicator_count=2
        ),
    )

    result = run(inputs, config=enabled_config)

    assert result.flags["ai_signal"] == "INCLUDED"
    # base visual (100, clean forensics) blended 50/50 with (1-0.8)*100=20 -> 60.
    assert result.visual_score == Decimal("60.00")
    assert any("anomaly-detection signal" in r.description for r in result.reason_codes)


def test_identical_inputs_produce_identical_scores() -> None:
    def build() -> TrustLayerInput:
        return TrustLayerInput(
            source_type=SourceTypeEnum.ORIGINAL_PDF,
            rows=_consistent_rows(),
            pdf_forensics=_clean_pdf_forensics(),
            statement_start_date=date(2026, 1, 1),
            statement_end_date=date(2026, 6, 30),
            declared_owner_name="Budi Santoso",
            detected_account_holder_name="Budi Santoso",
        )

    first = run(build())
    second = run(build())

    assert first.data_confidence_score == second.data_confidence_score
    assert first.band == second.band


def test_empty_rows_do_not_crash_and_score_zero_ocr() -> None:
    inputs = TrustLayerInput(
        source_type=SourceTypeEnum.ORIGINAL_PDF,
        rows=[],
        pdf_forensics=_clean_pdf_forensics(),
        statement_start_date=None,
        statement_end_date=None,
        declared_owner_name=None,
        detected_account_holder_name=None,
    )

    result = run(inputs)

    assert result.ocr_score == Decimal(0)
    assert result.completeness_score == Decimal("0.00")
