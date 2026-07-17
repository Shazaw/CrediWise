"""Assessment use case + analysis pipeline stage (PLAN §10.1, §8.2/§8.3;
FR-8, FR-9, FR-18). Sprint 4, T4.5/T4.6.

`AssessmentService` (a class, mirroring `DocumentService`) handles the
user-facing `POST /assessments` + `GET /assessments/{id}[...]` read paths.
`run_assessment_analysis` (a module function, mirroring
`extraction_service.run_extraction`/`verification_service.run_verification`)
is the async pipeline-stage body that actually runs Twin -> Risk ->
SafeBorrowing and is dispatched via `app/pipeline/dispatch.py
dispatch_assessment_analysis` (PLAN §8.3 sequence diagram: `POST /assessments`
enqueues `run_assessment`, distinct from the synchronous read endpoints).
"""

import hashlib
import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol, cast

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.engines import cash_flow_twin, risk, safe_borrowing
from app.engines.cash_flow_twin import TwinTransactionInput
from app.engines.config import model_config as cfg
from app.engines.risk import RiskInput
from app.engines.safe_borrowing import SafeBorrowingInput
from app.models.assessment import Assessment
from app.models.assessment_document import AssessmentDocument
from app.models.assessment_input_snapshot import AssessmentInputSnapshot
from app.models.assessment_reason_code import AssessmentReasonCode
from app.models.assessment_transaction import AssessmentTransaction
from app.models.cash_flow_event import CashFlowEvent
from app.models.enums import (
    ActorTypeEnum,
    AssessmentStatusEnum,
    BandEnum,
    DocStatusEnum,
    PipelineStageEnum,
    ReasonTypeEnum,
    SeverityEnum,
)
from app.models.financial_profile import FinancialProfile
from app.models.income_source import IncomeSource
from app.models.monthly_cash_flow_snapshot import MonthlyCashFlowSnapshot
from app.models.transaction import Transaction
from app.models.user import User
from app.pipeline.dispatch import dispatch_assessment_analysis
from app.repositories.assessment_reason_code_repository import AssessmentReasonCodeRepository
from app.repositories.assessment_repository import AssessmentRepository
from app.repositories.document_processing_run_repository import DocumentProcessingRunRepository
from app.repositories.document_verification_result_repository import (
    DocumentVerificationResultRepository,
)
from app.repositories.financial_profile_repository import FinancialProfileRepository
from app.repositories.financing_need_repository import FinancingNeedRepository
from app.repositories.model_version_repository import ModelVersionRepository
from app.repositories.source_document_repository import SourceDocumentRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services import audit_service
from app.services.pipeline_stage_tracking import track_assessment_stage


@dataclass(frozen=True)
class TwinView:
    profile: FinancialProfile
    monthly_snapshots: list[MonthlyCashFlowSnapshot]
    income_sources: list[IncomeSource]
    cash_flow_events: list[CashFlowEvent]


class AssessmentService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._assessments = AssessmentRepository(db)
        self._financing_needs = FinancingNeedRepository(db)
        self._documents = SourceDocumentRepository(db)
        self._processing_runs = DocumentProcessingRunRepository(db)
        self._verification_results = DocumentVerificationResultRepository(db)
        self._transactions = TransactionRepository(db)
        self._model_versions = ModelVersionRepository(db)
        self._profiles = FinancialProfileRepository(db)
        self._reason_codes = AssessmentReasonCodeRepository(db)

    def create(
        self,
        *,
        user: User,
        financing_need_id: uuid.UUID,
        source_document_ids: list[uuid.UUID],
    ) -> Assessment:
        """FR-18: freezes an immutable input snapshot over exactly the
        caller's confirmed+normalized documents, then dispatches the async
        analysis stage (PLAN §8.3)."""
        financing_need = self._financing_needs.get_by_id(financing_need_id)
        if financing_need is None or financing_need.user_id != user.id:
            raise NotFoundError("Financing need not found")
        if not source_document_ids:
            raise ValidationError("At least one source document is required")

        documents = []
        for document_id in source_document_ids:
            document = self._documents.get_by_id(document_id)
            if document is None or document.user_id != user.id:
                raise NotFoundError("Document not found")
            if document.status != DocStatusEnum.ANALYZING:
                raise ValidationError(
                    "Document is not ready for assessment (must be reviewed, confirmed, "
                    "and normalized first)",
                    details={"document_id": str(document_id), "status": document.status.value},
                )
            documents.append(document)

        model_version = self._model_versions.get_active(cfg.MODEL_NAME)
        assert model_version is not None  # noqa: S101 - seeded at bootstrap (T1.7)

        assessment = Assessment(
            id=uuid.uuid4(),
            user_id=user.id,
            financing_need_id=financing_need.id,
            model_version_id=model_version.id,
            status=AssessmentStatusEnum.PENDING,
        )
        self._assessments.add(assessment)

        parser_versions: dict[str, str] = {}
        document_links: list[AssessmentDocument] = []
        for document in documents:
            processing_run = self._processing_runs.get_latest_for_document(document.id)
            verification_result = self._verification_results.get_latest_for_document(document.id)
            if processing_run is None or verification_result is None:
                raise ValidationError(
                    "Document is missing extraction/verification lineage",
                    details={"document_id": str(document.id)},
                )
            parser_versions[str(document.id)] = processing_run.parser_version
            document_links.append(
                AssessmentDocument(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    source_document_id=document.id,
                    processing_run_id=processing_run.id,
                    verification_result_id=verification_result.id,
                )
            )
        self._assessments.add_document_links(document_links)

        document_ids = [d.id for d in documents]
        transactions = self._transactions.list_for_documents(document_ids)
        transaction_links = [
            AssessmentTransaction(id=uuid.uuid4(), assessment_id=assessment.id, transaction_id=t.id)
            for t in transactions
        ]
        self._assessments.add_transaction_links(transaction_links)

        snapshot = AssessmentInputSnapshot(
            id=uuid.uuid4(),
            assessment_id=assessment.id,
            snapshot_hash=_snapshot_hash(
                document_ids, [t.id for t in transactions], financing_need.id
            ),
            normalized_input_json={"transaction_count": len(transactions)},
            document_refs_json={"document_ids": [str(d) for d in document_ids]},
            transaction_refs_json={"transaction_ids": [str(t.id) for t in transactions]},
            accepted_corrections_json={},
            parser_versions_json=parser_versions,
            categorizer_version=cfg.MODEL_VERSION,
            engine_config_hash=cfg.config_hash(),
            simulation_parameters_json={},
            offer_terms_json={},
        )
        self._assessments.add_snapshot(snapshot)

        audit_service.record(
            self._db,
            actor_type=ActorTypeEnum.USER,
            actor_id=user.id,
            action="assessment.created",
            entity_type="assessment",
            entity_id=assessment.id,
            metadata={"document_count": len(documents), "transaction_count": len(transactions)},
        )
        self._db.commit()

        dispatch_assessment_analysis(assessment.id)

        return assessment

    def get(self, user: User, assessment_id: uuid.UUID) -> Assessment:
        return self._get_owned(user, assessment_id)

    def get_twin(self, user: User, assessment_id: uuid.UUID) -> TwinView:
        assessment = self._get_owned(user, assessment_id)
        profile = self._profiles.get_profile_for_assessment(assessment.id)
        if profile is None:
            raise NotFoundError("Twin not available yet")
        return TwinView(
            profile=profile,
            monthly_snapshots=self._profiles.get_monthly_snapshots_for_assessment(assessment.id),
            income_sources=self._profiles.get_income_sources_for_assessment(assessment.id),
            cash_flow_events=self._profiles.get_cash_flow_events_for_assessment(assessment.id),
        )

    def get_reason_codes(self, user: User, assessment_id: uuid.UUID) -> list[AssessmentReasonCode]:
        assessment = self._get_owned(user, assessment_id)
        return self._reason_codes.list_for_assessment(assessment.id)

    def get_lineage(self, user: User, assessment_id: uuid.UUID) -> AssessmentInputSnapshot:
        """FR-18/NFR-17: exact snapshot/parser/model/input hashes (PLAN §12.2
        `GET /assessments/{id}/lineage`)."""
        assessment = self._get_owned(user, assessment_id)
        snapshot = self._assessments.get_snapshot(assessment.id)
        if snapshot is None:
            raise NotFoundError("Lineage not available yet")
        return snapshot

    def _get_owned(self, user: User, assessment_id: uuid.UUID) -> Assessment:
        assessment = self._assessments.get_by_id(assessment_id)
        if assessment is None or assessment.user_id != user.id:
            raise NotFoundError("Assessment not found")
        return assessment


def _snapshot_hash(
    document_ids: list[uuid.UUID], transaction_ids: list[uuid.UUID], financing_need_id: uuid.UUID
) -> str:
    canonical = json.dumps(
        {
            "document_ids": sorted(str(d) for d in document_ids),
            "transaction_ids": sorted(str(t) for t in transaction_ids),
            "financing_need_id": str(financing_need_id),
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def run_assessment_analysis(db: Session, assessment_id: uuid.UUID) -> None:
    """Idempotent/resumable per NFR-3: an assessment not sitting in
    `PENDING` has already been analyzed (or is terminal), so a retry is a
    no-op. Runs `CashFlowTwinEngine` -> `RiskEngine` -> `SafeBorrowingEngine`
    (PLAN §8.3) and persists their outputs; `ShockEngine`/`OfferEngine`
    (Sprint 5) extend this same task later, not this cycle."""
    assessments = AssessmentRepository(db)
    assessment = assessments.get_by_id(assessment_id)
    if assessment is None or assessment.status != AssessmentStatusEnum.PENDING:
        return

    with track_assessment_stage(db, assessment.id, PipelineStageEnum.ANALYSIS):
        financing_need = FinancingNeedRepository(db).get_by_id(assessment.financing_need_id)
        assert financing_need is not None  # noqa: S101 - FK guarantees existence

        transaction_links = assessments.get_transaction_links(assessment.id)
        transactions = TransactionRepository(db).get_by_ids(
            [link.transaction_id for link in transaction_links]
        )
        twin_result = cash_flow_twin.run([_to_twin_input(t) for t in transactions])

        document_links = assessments.get_document_links(assessment.id)
        verification_repo = DocumentVerificationResultRepository(db)
        verification_results = [
            v
            for v in (
                verification_repo.get_by_id(link.verification_result_id) for link in document_links
            )
            if v is not None
        ]
        data_confidence_score = _mean_decimal(v.data_confidence_score for v in verification_results)
        data_confidence_band = (
            band_from_score(data_confidence_score) if data_confidence_score is not None else None
        )
        ocr_avg = _mean_decimal(v.ocr_score for v in verification_results)
        ownership_avg = _mean_decimal(v.ownership_score for v in verification_results)
        completeness_avg = _mean_decimal(v.completeness_score for v in verification_results)

        income_concentration = max(
            (s.concentration_ratio for s in twin_result.income_sources), default=None
        )
        risk_result = risk.run(
            RiskInput(
                median_income=twin_result.median_income,
                essential_expenses=twin_result.essential_expenses,
                discretionary_expenses=twin_result.discretionary_expenses,
                existing_debt_service=twin_result.existing_debt,
                positive_cash_flow_ratio=twin_result.positive_cash_flow_ratio,
                income_volatility=twin_result.income_volatility,
                months_covered=twin_result.months_covered,
                data_confidence_band=data_confidence_band,
                income_concentration_ratio=income_concentration,
                ocr_score=ocr_avg,
                ownership_score=ownership_avg,
                completeness_score=completeness_avg,
            )
        )

        dominant_source = max(
            twin_result.income_sources, key=lambda s: s.concentration_ratio, default=None
        )
        min_minimum_balance = (
            min(m.minimum_balance for m in twin_result.monthly_snapshots)
            if twin_result.monthly_snapshots
            else None
        )
        safe_borrowing_result = safe_borrowing.run(
            SafeBorrowingInput(
                median_income=twin_result.median_income,
                essential_expenses=twin_result.essential_expenses,
                existing_debt_service=twin_result.existing_debt,
                income_volatility=twin_result.income_volatility,
                weakest_month_cash_flow=twin_result.weakest_month_cash_flow,
                average_free_cash_flow=twin_result.average_free_cash_flow,
                requested_amount=financing_need.requested_amount,
                min_monthly_minimum_balance=min_minimum_balance,
                dominant_income_day=dominant_source.dominant_arrival_day
                if dominant_source
                else None,
                dominant_income_frequency=dominant_source.frequency if dominant_source else None,
            )
        )

        _persist_twin(db, assessment, twin_result)
        _persist_reason_codes(db, assessment.id, twin_result, risk_result, safe_borrowing_result)

        assessment.data_confidence_score = data_confidence_score
        assessment.indicative_risk_band = risk_result.band
        assessment.model_confidence = risk_result.model_confidence
        assessment.safe_loan_amount = safe_borrowing_result.safe_loan_amount
        assessment.maximum_safe_instalment = safe_borrowing_result.maximum_safe_instalment
        assessment.recommended_tenor_months = safe_borrowing_result.recommended_tenor_months
        assessment.recommended_due_date_start = safe_borrowing_result.recommended_due_date_start
        assessment.recommended_due_date_end = safe_borrowing_result.recommended_due_date_end
        assessment.recommended_frequency = safe_borrowing_result.recommended_frequency
        assessment.status = AssessmentStatusEnum.COMPLETE
        db.flush()

        documents_repo = SourceDocumentRepository(db)
        for link in document_links:
            document = documents_repo.get_by_id(link.source_document_id)
            if document is not None and document.status == DocStatusEnum.ANALYZING:
                document.status = DocStatusEnum.COMPLETE
        db.flush()

        audit_service.record(
            db,
            actor_type=ActorTypeEnum.SYSTEM,
            actor_id=None,
            action="assessment.analysis_completed",
            entity_type="assessment",
            entity_id=assessment.id,
            metadata={"risk_band": risk_result.band.value, "status": assessment.status.value},
        )
        db.commit()


def _to_twin_input(transaction: Transaction) -> TwinTransactionInput:
    return TwinTransactionInput(
        transaction_id=transaction.id,
        transaction_date=transaction.transaction_date,
        amount=transaction.amount,
        direction=transaction.direction,
        category=transaction.category,
        transaction_context=transaction.transaction_context,
        subcategory=transaction.subcategory,
        normalized_merchant=transaction.normalized_merchant or transaction.raw_description,
        is_internal_transfer=transaction.is_internal_transfer,
        balance_after=transaction.balance_after,
    )


def _mean_decimal(values: Iterable[Decimal | None]) -> Decimal | None:
    values_list = [v for v in values if v is not None]
    if not values_list:
        return None
    return sum(values_list, start=Decimal(0)) / len(values_list)


def band_from_score(score: Decimal) -> BandEnum:
    thresholds = cfg.CONFIG["trust_layer"]["band_thresholds"]  # type: ignore[index]
    if score >= thresholds["high"]:
        return BandEnum.HIGH
    if score >= thresholds["medium"]:
        return BandEnum.MEDIUM
    return BandEnum.LOW


def _persist_twin(
    db: Session, assessment: Assessment, twin_result: cash_flow_twin.FinancialProfileResult
) -> None:
    profiles = FinancialProfileRepository(db)
    profiles.add_profile(
        FinancialProfile(
            id=uuid.uuid4(),
            user_id=assessment.user_id,
            assessment_id=assessment.id,
            average_income=twin_result.average_income,
            median_income=twin_result.median_income,
            income_volatility=twin_result.income_volatility,
            essential_expenses=twin_result.essential_expenses,
            discretionary_expenses=twin_result.discretionary_expenses,
            existing_debt=twin_result.existing_debt,
            average_free_cash_flow=twin_result.average_free_cash_flow,
            minimum_balance=twin_result.minimum_balance,
            positive_cash_flow_ratio=twin_result.positive_cash_flow_ratio,
            weakest_month_cash_flow=twin_result.weakest_month_cash_flow,
            savings_buffer=twin_result.savings_buffer,
            months_covered=twin_result.months_covered,
            coverage_flag=twin_result.coverage_flag,
            generated_at=datetime.now(UTC),
        )
    )

    if twin_result.monthly_snapshots:
        profiles.add_monthly_snapshots(
            [
                MonthlyCashFlowSnapshot(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    year_month=m.year_month,
                    personal_income=m.personal_income,
                    business_income=m.business_income,
                    essential_expenses=m.essential_expenses,
                    discretionary_expenses=m.discretionary_expenses,
                    business_expenses=m.business_expenses,
                    debt_service=m.debt_service,
                    opening_balance=m.opening_balance,
                    minimum_balance=m.minimum_balance,
                    closing_balance=m.closing_balance,
                    net_cash_flow=m.net_cash_flow,
                )
                for m in twin_result.monthly_snapshots
            ]
        )

    if twin_result.income_sources:
        profiles.add_income_sources(
            [
                IncomeSource(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    source_name=s.source_name,
                    source_type=s.source_type,
                    average_amount=s.average_amount,
                    frequency=s.frequency,
                    volatility=s.volatility,
                    concentration_ratio=s.concentration_ratio,
                    dominant_arrival_day=s.dominant_arrival_day,
                    confidence=s.confidence,
                )
                for s in twin_result.income_sources
            ]
        )

    if twin_result.cash_flow_events:
        profiles.add_cash_flow_events(
            [
                CashFlowEvent(
                    id=uuid.uuid4(),
                    assessment_id=assessment.id,
                    event_date=None,
                    expected_day_of_month=e.expected_day_of_month,
                    amount=e.amount,
                    direction=e.direction,
                    event_type=e.event_type,
                    recurring_series_id=None,
                    confidence=e.confidence,
                )
                for e in twin_result.cash_flow_events
            ]
        )


class _ReasonCodeLike(Protocol):
    """Structural type covering `cash_flow_twin.ReasonCode`/`risk.ReasonCode`/
    `safe_borrowing.ReasonCode` — each engine defines its own identical
    dataclass rather than sharing one (PLAN §10.1: engines depend on
    nothing but their own inputs and `model_config`, not on each other)."""

    code: str
    description: str


_POSITIVE_MARKERS = ("EXCELLENT", "STRONG", "CLEAN", "MATCHED", "SELECTED", "GOOD")
_HIGH_SEVERITY_MARKERS = ("ZERO", "INSUFFICIENT")
_MEDIUM_SEVERITY_MARKERS = ("WEAK", "MISMATCH", "LIMITED_BY", "HIGH", "CAUTION", "CONCENTRATION")


def _classify_reason(code: str) -> tuple[ReasonTypeEnum, SeverityEnum]:
    """Sprint 4 gap-fill (§24.11): PLAN §11.3 names `assessment_reason_codes
    .reason_type`/`.severity` as required columns but not a mapping from
    engine reason codes to them -- a lightweight, documented heuristic over
    each engine's own code-naming convention (see each engine's `run()`)."""
    if code == "RISK_INSUFFICIENT_DATA":
        return ReasonTypeEnum.DATA_QUALITY, SeverityEnum.HIGH
    if code.startswith(("TWIN_", "NORMALIZATION_")):
        return ReasonTypeEnum.DATA_QUALITY, SeverityEnum.INFO

    if any(marker in code for marker in _POSITIVE_MARKERS):
        return ReasonTypeEnum.POSITIVE, SeverityEnum.INFO
    if any(marker in code for marker in _HIGH_SEVERITY_MARKERS):
        return ReasonTypeEnum.RISK, SeverityEnum.HIGH
    if any(marker in code for marker in _MEDIUM_SEVERITY_MARKERS):
        return ReasonTypeEnum.RISK, SeverityEnum.MEDIUM
    return ReasonTypeEnum.RISK, SeverityEnum.LOW


def _persist_reason_codes(
    db: Session,
    assessment_id: uuid.UUID,
    twin_result: cash_flow_twin.FinancialProfileResult,
    risk_result: risk.RiskResult,
    safe_borrowing_result: safe_borrowing.RecommendationResult,
) -> None:
    all_reasons: tuple[_ReasonCodeLike, ...] = (
        *cast("list[_ReasonCodeLike]", twin_result.reason_codes),
        *cast("list[_ReasonCodeLike]", risk_result.reason_codes),
        *cast("list[_ReasonCodeLike]", safe_borrowing_result.reason_codes),
    )
    if not all_reasons:
        return
    rows = []
    for reason in all_reasons:
        reason_type, severity = _classify_reason(reason.code)
        rows.append(
            AssessmentReasonCode(
                id=uuid.uuid4(),
                assessment_id=assessment_id,
                reason_type=reason_type,
                reason_code=reason.code,
                description=reason.description,
                severity=severity,
                evidence_json={},
            )
        )
    AssessmentReasonCodeRepository(db).add_all(rows)
