"""Normalization pipeline stage (PLAN §8.2 `NORMALIZING -> ANALYZING`;
§15.3-adjacent, FR-6). Sprint 4, T4.1.

Mirrors `verification_service.run_verification`'s shape. Re-derives
categorization over *every* active transaction the triggering document's
user owns (not just this document's own rows) so `NormalizationEngine`'s
internal-transfer and recurring detection see the whole multi-account
picture FR-6 AC5 requires (see that engine's module docstring). Re-running
against an unchanged transaction set is idempotent (NFR-3): the engine is
pure, so writing its output back is a no-op in effect even though the rows
are unconditionally re-saved.
"""

import uuid

from sqlalchemy.orm import Session

from app.engines import normalization
from app.engines.normalization import NormalizationTransactionInput
from app.models.enums import ActorTypeEnum, DocStatusEnum, PipelineStageEnum
from app.models.recurring_series import RecurringSeries
from app.models.transaction import Transaction
from app.repositories.recurring_series_repository import RecurringSeriesRepository
from app.repositories.source_document_repository import SourceDocumentRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services import audit_service
from app.services.pipeline_stage_tracking import track_stage


def run_normalization(db: Session, document_id: uuid.UUID) -> None:
    """Idempotent/resumable per NFR-3: a document not sitting in
    `NORMALIZING` has already been normalized (or is terminal), so a retry
    is a no-op."""
    documents = SourceDocumentRepository(db)
    document = documents.get_by_id(document_id)
    if document is None or document.status != DocStatusEnum.NORMALIZING:
        return

    with track_stage(db, document.id, PipelineStageEnum.NORMALIZATION):
        transactions = TransactionRepository(db).list_for_user(document.user_id)
        by_id = {t.id: t for t in transactions}

        result = normalization.run([_to_engine_input(t) for t in transactions])

        for update in result.updates:
            transaction = by_id[update.transaction_id]
            transaction.category = update.category
            transaction.subcategory = update.subcategory
            transaction.transaction_context = update.transaction_context
            transaction.normalized_merchant = update.normalized_merchant
            transaction.is_internal_transfer = update.is_internal_transfer
            transaction.is_recurring = update.is_recurring
            transaction.category_confidence = update.category_confidence

        _upsert_recurring_series(db, document.user_id, result.recurring_series)

        document.status = DocStatusEnum.ANALYZING
        db.flush()
        audit_service.record(
            db,
            actor_type=ActorTypeEnum.SYSTEM,
            actor_id=None,
            action="document.normalization_completed",
            entity_type="source_document",
            entity_id=document.id,
            metadata={
                "categorized_count": len(result.updates),
                "recurring_series_count": len(result.recurring_series),
            },
        )
        db.commit()


def _to_engine_input(transaction: Transaction) -> NormalizationTransactionInput:
    return NormalizationTransactionInput(
        transaction_id=transaction.id,
        financial_account_id=transaction.financial_account_id,
        transaction_date=transaction.transaction_date,
        amount=transaction.amount,
        direction=transaction.direction,
        raw_description=transaction.raw_description,
    )


def _upsert_recurring_series(
    db: Session,
    user_id: uuid.UUID,
    detected: list[normalization.DetectedRecurringSeries],
) -> None:
    repo = RecurringSeriesRepository(db)
    for series in detected:
        existing = repo.get_by_identity(
            user_id=user_id,
            financial_account_id=series.financial_account_id,
            series_type=series.series_type,
            normalized_counterparty=series.normalized_counterparty,
        )
        if existing is not None:
            existing.median_amount = series.median_amount
            existing.expected_interval_days = series.expected_interval_days
            existing.expected_day_of_month = series.expected_day_of_month
            existing.regularity_score = series.regularity_score
            existing.confidence = series.confidence
            continue

        repo.add(
            RecurringSeries(
                id=uuid.uuid4(),
                user_id=user_id,
                financial_account_id=series.financial_account_id,
                series_type=series.series_type,
                normalized_counterparty=series.normalized_counterparty,
                median_amount=series.median_amount,
                expected_interval_days=series.expected_interval_days,
                expected_day_of_month=series.expected_day_of_month,
                regularity_score=series.regularity_score,
                confidence=series.confidence,
            )
        )
