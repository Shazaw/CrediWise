"""`TrustLayerEngine` — Data Confidence Score (PLAN §5.2, §15.1, §15.3; FR-5).

Pure per PLAN §10.1 Golden Rule 3: no DB, network, filesystem, clock, or
RNG. Inputs are already-extracted rows/forensics/evidence; the service
layer (`app/services/verification_service.py`) does all I/O (storage
reads, the optional local-Kimi call) before calling `run()`.

7 weighted sub-scores (§5.2) aggregate to `data_confidence_score` (0-100)
with a band and reason codes. §2.3/§5.2's positioning guardrail applies to
every reason string this engine produces: low confidence is phrased as
unverifiable data, never as dishonesty or fraud.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.engines.config import model_config as cfg
from app.engines.extraction.schema import ExtractedRow, PdfForensics, RowDirection
from app.models.enums import BandEnum, SourceTypeEnum

_RECOMMENDATION_COPY = (
    "We can't fully verify this data yet. Upload the original PDF or "
    "connect your account for a more verified assessment."
)

_TITLE_PREFIXES = frozenset(
    {"BAPAK", "IBU", "BPK", "SDR", "SDRI", "MR", "MRS", "MS", "DR", "TUAN", "NYONYA"}
)


@dataclass(frozen=True)
class KimiAnomalyEvidence:
    """Engine-local evidence type — deliberately not the `local_ai`
    integration's Pydantic schema, so `engines/` never imports from
    `integrations/` (PLAN §10.1 dependency direction). The service layer
    maps `DocumentAnomalyResponse` onto this before calling `run()`."""

    available: bool
    anomaly_probability: Decimal
    indicator_count: int


@dataclass(frozen=True)
class TrustLayerInput:
    source_type: SourceTypeEnum
    rows: list[ExtractedRow]
    pdf_forensics: PdfForensics | None
    statement_start_date: date | None
    statement_end_date: date | None
    declared_owner_name: str | None
    detected_account_holder_name: str | None
    kimi_evidence: KimiAnomalyEvidence | None = None


@dataclass(frozen=True)
class ReasonCode:
    code: str
    description: str


@dataclass(frozen=True)
class TrustLayerConfig:
    weights: dict[str, Decimal]
    provenance_tiers: dict[str, int]
    band_high_threshold: int
    band_medium_threshold: int
    completeness_target_months: int
    metadata: dict[str, int]
    visual: dict[str, int]
    consistency: dict[str, int]
    ownership: dict[str, int]
    kimi_anomaly_scoring_enabled: bool
    kimi_weight_within_visual: Decimal


@dataclass(frozen=True)
class DataConfidenceResult:
    provenance_score: Decimal
    consistency_score: Decimal
    metadata_score: Decimal
    ocr_score: Decimal
    visual_score: Decimal
    completeness_score: Decimal
    ownership_score: Decimal
    data_confidence_score: Decimal
    band: BandEnum
    reason_codes: list[ReasonCode] = field(default_factory=list)
    recommendation: str | None = None
    flags: dict[str, str] = field(default_factory=dict)


def default_config() -> TrustLayerConfig:
    """Builds the typed engine config from the versioned `model_config.CONFIG`
    (PLAN §19.2's single source of truth for weights/thresholds)."""
    raw = cfg.CONFIG["trust_layer"]
    assert isinstance(raw, dict)  # noqa: S101 - internal invariant, not user input
    return TrustLayerConfig(
        weights=raw["weights"],
        provenance_tiers=raw["provenance_tiers"],
        band_high_threshold=raw["band_thresholds"]["high"],
        band_medium_threshold=raw["band_thresholds"]["medium"],
        completeness_target_months=raw["completeness_target_months"],
        metadata=raw["metadata"],
        visual=raw["visual"],
        consistency=raw["consistency"],
        ownership=raw["ownership"],
        kimi_anomaly_scoring_enabled=raw["kimi"]["anomaly_scoring_enabled"],
        kimi_weight_within_visual=raw["kimi"]["weight_within_visual"],
    )


DEFAULT_CONFIG = default_config()


def run(inputs: TrustLayerInput, config: TrustLayerConfig = DEFAULT_CONFIG) -> DataConfidenceResult:
    reason_codes: list[ReasonCode] = []
    flags: dict[str, str] = {}

    provenance_score, provenance_reasons = _score_provenance(inputs.source_type, config)
    consistency_score, consistency_reasons = _score_consistency(inputs.rows, config)
    metadata_score, metadata_reasons = _score_metadata(inputs.pdf_forensics, config)
    ocr_score, ocr_reasons = _score_ocr(inputs.rows)
    visual_score, visual_reasons, ai_signal = _score_visual(
        inputs.pdf_forensics, inputs.rows, inputs.kimi_evidence, config
    )
    completeness_score, completeness_reasons = _score_completeness(
        inputs.statement_start_date, inputs.statement_end_date, inputs.rows, config
    )
    ownership_score, ownership_reasons = _score_ownership(
        inputs.declared_owner_name, inputs.detected_account_holder_name, config
    )
    flags["ai_signal"] = ai_signal

    reason_codes.extend(provenance_reasons)
    reason_codes.extend(consistency_reasons)
    reason_codes.extend(metadata_reasons)
    reason_codes.extend(ocr_reasons)
    reason_codes.extend(visual_reasons)
    reason_codes.extend(completeness_reasons)
    reason_codes.extend(ownership_reasons)

    sub_scores = {
        "provenance": provenance_score,
        "consistency": consistency_score,
        "metadata": metadata_score,
        "ocr": ocr_score,
        "visual": visual_score,
        "completeness": completeness_score,
        "ownership": ownership_score,
    }
    weighted_total = sum(
        (config.weights[name] * score for name, score in sub_scores.items()), start=Decimal("0")
    )
    data_confidence_score = weighted_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    band = _band_for(data_confidence_score, config)

    recommendation = _RECOMMENDATION_COPY if band is not BandEnum.HIGH else None

    return DataConfidenceResult(
        provenance_score=provenance_score,
        consistency_score=consistency_score,
        metadata_score=metadata_score,
        ocr_score=ocr_score,
        visual_score=visual_score,
        completeness_score=completeness_score,
        ownership_score=ownership_score,
        data_confidence_score=data_confidence_score,
        band=band,
        reason_codes=reason_codes,
        recommendation=recommendation,
        flags=flags,
    )


def _band_for(score: Decimal, config: TrustLayerConfig) -> BandEnum:
    if score >= config.band_high_threshold:
        return BandEnum.HIGH
    if score >= config.band_medium_threshold:
        return BandEnum.MEDIUM
    return BandEnum.LOW


def _score_provenance(
    source_type: SourceTypeEnum, config: TrustLayerConfig
) -> tuple[Decimal, list[ReasonCode]]:
    tier = config.provenance_tiers.get(source_type.value, 0)
    reason = ReasonCode(
        code=f"PROVENANCE_{source_type.value}",
        description=f"Source: {source_type.value.replace('_', ' ').title()}",
    )
    return Decimal(tier), [reason]


def _score_consistency(
    rows: list[ExtractedRow], config: TrustLayerConfig
) -> tuple[Decimal, list[ReasonCode]]:
    checked = 0
    matched = 0
    for previous, current in zip(rows, rows[1:], strict=False):
        if previous.balance_after is None or current.balance_after is None:
            continue
        checked += 1
        delta = current.amount if current.direction is RowDirection.CREDIT else -current.amount
        expected = previous.balance_after + delta
        if expected == current.balance_after:
            matched += 1

    if checked == 0:
        score = Decimal(config.consistency["no_balance_data_default"])
        reason = ReasonCode(
            code="CONSISTENCY_NO_BALANCE_DATA",
            description="No consecutive balance data available to reconstruct",
        )
        return score, [reason]

    ratio = Decimal(matched) / Decimal(checked)
    score = (ratio * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if matched == checked:
        reason = ReasonCode(code="CONSISTENCY_MATCHED", description="Balance sequence consistent")
    else:
        mismatched = checked - matched
        reason = ReasonCode(
            code="CONSISTENCY_MISMATCH",
            description=f"{mismatched} of {checked} balance row(s) did not reconcile",
        )
    return score, [reason]


def _score_metadata(
    forensics: PdfForensics | None, config: TrustLayerConfig
) -> tuple[Decimal, list[ReasonCode]]:
    m = config.metadata
    if forensics is None:
        reason = ReasonCode(
            code="METADATA_UNAVAILABLE",
            description="No document metadata available for this source type",
        )
        return Decimal(m["no_forensics_base"]), [reason]

    score = m["base"]
    reasons: list[ReasonCode] = []
    if forensics.creation_date is None:
        score -= m["missing_creation_date_penalty"]
        reasons.append(
            ReasonCode(
                code="METADATA_MISSING_CREATION_DATE",
                description="Document has no creation-date metadata",
            )
        )
    if not forensics.producer and not forensics.creator:
        score -= m["missing_producer_penalty"]
        reasons.append(
            ReasonCode(
                code="METADATA_MISSING_PRODUCER",
                description="Document has no producer/creator metadata",
            )
        )
    if forensics.incremental_update_count > 0:
        penalty = min(
            forensics.incremental_update_count * m["incremental_update_penalty_per_update"],
            m["incremental_update_penalty_cap"],
        )
        score -= penalty
        reasons.append(
            ReasonCode(
                code="METADATA_INCREMENTAL_EDITS",
                description=(
                    f"Document was saved {forensics.incremental_update_count} additional "
                    "time(s) after its original creation"
                ),
            )
        )
    if forensics.has_digital_signature:
        score += m["signature_bonus"]
        reasons.append(
            ReasonCode(code="METADATA_SIGNED", description="Document carries a digital signature")
        )

    score = max(0, min(100, score))
    if not reasons:
        reasons.append(
            ReasonCode(
                code="METADATA_CLEAN",
                description="Document metadata is consistent with an unmodified original",
            )
        )
    return Decimal(score), reasons


def _score_ocr(rows: list[ExtractedRow]) -> tuple[Decimal, list[ReasonCode]]:
    if not rows:
        return Decimal(0), [
            ReasonCode(code="OCR_NO_ROWS", description="No extracted rows to assess")
        ]
    mean_confidence = sum((row.extraction_confidence for row in rows), Decimal("0")) / len(rows)
    score = (mean_confidence * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    reason = ReasonCode(
        code="OCR_MEAN_CONFIDENCE",
        description=f"Mean extraction confidence across {len(rows)} row(s): {score}%",
    )
    return score, [reason]


def _score_visual(
    forensics: PdfForensics | None,
    rows: list[ExtractedRow],
    kimi_evidence: KimiAnomalyEvidence | None,
    config: TrustLayerConfig,
) -> tuple[Decimal, list[ReasonCode], str]:
    v = config.visual
    reasons: list[ReasonCode] = []

    if forensics is None:
        score = Decimal(v["no_forensics_base"])
        reasons.append(
            ReasonCode(
                code="VISUAL_UNAVAILABLE",
                description="No structural forensics available for this source type",
            )
        )
    else:
        score = Decimal(v["base"])
        if forensics.distinct_font_count > v["excess_font_threshold"]:
            score -= v["excess_font_penalty"]
            reasons.append(
                ReasonCode(
                    code="VISUAL_FONT_VARIETY",
                    description=(
                        f"Possible visual inconsistency detected: {forensics.distinct_font_count} "
                        "distinct fonts in one statement"
                    ),
                )
            )

        duplicate_count = _count_duplicate_rows(rows)
        if duplicate_count > 0:
            score -= v["duplicate_row_penalty"]
            reasons.append(
                ReasonCode(
                    code="VISUAL_DUPLICATE_ROWS",
                    description=(
                        f"Possible visual inconsistency detected: {duplicate_count} duplicate "
                        "transaction row(s)"
                    ),
                )
            )

    ai_signal = "DISABLED"
    if kimi_evidence is not None:
        if not kimi_evidence.available:
            ai_signal = "UNAVAILABLE"
        elif config.kimi_anomaly_scoring_enabled:
            ai_signal = "INCLUDED"
            kimi_component = (Decimal(100) - kimi_evidence.anomaly_probability * 100).quantize(
                Decimal("0.01")
            )
            weight = config.kimi_weight_within_visual
            score = score * (Decimal(1) - weight) + kimi_component * weight
            if kimi_evidence.indicator_count > 0:
                reasons.append(
                    ReasonCode(
                        code="VISUAL_AI_ANOMALY_SIGNAL",
                        description=(
                            f"Local anomaly-detection signal flagged {kimi_evidence.indicator_count} "
                            "possible visual inconsistency indicator(s)"
                        ),
                    )
                )

    score = max(Decimal(0), min(Decimal(100), score))
    if not reasons:
        reasons.append(
            ReasonCode(code="VISUAL_CLEAN", description="No visual/structural anomalies detected")
        )
    return score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), reasons, ai_signal


def _count_duplicate_rows(rows: list[ExtractedRow]) -> int:
    seen: set[tuple[date, int, str, RowDirection]] = set()
    duplicates = 0
    for row in rows:
        key = (row.transaction_date, row.amount, row.raw_description, row.direction)
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return duplicates


def _score_completeness(
    statement_start: date | None,
    statement_end: date | None,
    rows: list[ExtractedRow],
    config: TrustLayerConfig,
) -> tuple[Decimal, list[ReasonCode]]:
    if statement_start is not None and statement_end is not None:
        months_covered = (
            (statement_end.year - statement_start.year) * 12
            + (statement_end.month - statement_start.month)
            + 1
        )
    elif rows:
        months_covered = len(
            {(row.transaction_date.year, row.transaction_date.month) for row in rows}
        )
    else:
        months_covered = 0

    target = config.completeness_target_months
    ratio = min(Decimal(months_covered) / Decimal(target), Decimal(1))
    score = (ratio * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if months_covered >= target:
        reason = ReasonCode(
            code="COMPLETENESS_TARGET_MET", description="Meets target statement coverage"
        )
    else:
        reason = ReasonCode(
            code="COMPLETENESS_PARTIAL",
            description=f"Covers {months_covered} of {target} target month(s)",
        )
    return score, [reason]


def _score_ownership(
    declared_name: str | None, detected_name: str | None, config: TrustLayerConfig
) -> tuple[Decimal, list[ReasonCode]]:
    o = config.ownership
    if not declared_name or not detected_name:
        reason = ReasonCode(
            code="OWNERSHIP_NOT_VERIFIABLE",
            description="No account-holder name available on the document to compare",
        )
        return Decimal(o["no_name_default"]), [reason]

    declared_tokens = _normalize_name_tokens(declared_name)
    detected_tokens = _normalize_name_tokens(detected_name)

    if declared_tokens == detected_tokens and declared_tokens:
        reason = ReasonCode(
            code="OWNERSHIP_MATCH", description="Account holder name matches profile"
        )
        return Decimal(o["exact_match"]), [reason]

    if not declared_tokens or not detected_tokens:
        reason = ReasonCode(
            code="OWNERSHIP_NOT_VERIFIABLE", description="Account holder name could not be compared"
        )
        return Decimal(o["no_name_default"]), [reason]

    overlap = len(declared_tokens & detected_tokens) / len(declared_tokens | detected_tokens)
    if overlap >= 0.5:
        score = o["partial_match_floor"] + (100 - o["partial_match_floor"]) * overlap
        reason = ReasonCode(
            code="OWNERSHIP_PARTIAL_MATCH",
            description="Account holder name partially matches profile (tolerant of initials/spacing)",
        )
        return Decimal(score).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), [reason]

    reason = ReasonCode(
        code="OWNERSHIP_MISMATCH",
        description="Account holder name does not clearly match profile",
    )
    return Decimal(o["mismatch"]), [reason]


def _normalize_name_tokens(name: str) -> set[str]:
    tokens = {token.strip(".,").upper() for token in name.split()}
    return {token for token in tokens if token and token not in _TITLE_PREFIXES}
