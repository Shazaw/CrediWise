"""Trust-Layer verification pipeline stage (PLAN §8.2 `VERIFYING ->
REVIEW_PENDING`; §15.3; FR-5). Sprint 3, T3.3/T3.4.

Re-derives the extraction result (rows + PDF forensics) from the same
immutable raw bytes already used by `extraction_service.run_extraction`,
rather than persisting `PdfForensics` as a new column or reading rows back
from `transactions`. This keeps the two pipeline stages independently
resumable per NFR-3 without an extra schema column: re-parsing
already-fetched, unchanged bytes is deterministic and cheap (no network
call), and the persisted `document_processing_runs.output_hash` from the
extraction stage lets a future reproducibility check confirm the re-parse
matches what was originally extracted.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.engines.extraction import extract
from app.engines.trust_layer import KimiAnomalyEvidence, TrustLayerInput
from app.engines.trust_layer import run as run_trust_layer
from app.integrations.local_ai import get_document_anomaly_port
from app.integrations.local_ai.schemas import AnalysisStatus, DocumentAnomalyRequest
from app.integrations.storage import get_storage_port
from app.models.document_verification_result import DocumentVerificationResult
from app.models.enums import ActorTypeEnum, DocStatusEnum, PipelineStageEnum
from app.repositories.document_processing_run_repository import DocumentProcessingRunRepository
from app.repositories.document_verification_result_repository import (
    DocumentVerificationResultRepository,
)
from app.repositories.model_version_repository import ModelVersionRepository
from app.repositories.source_document_repository import SourceDocumentRepository
from app.repositories.user_repository import UserRepository
from app.services import audit_service
from app.services.extraction_service import maybe_recognize_text
from app.services.pipeline_stage_tracking import track_stage


def run_verification(db: Session, document_id: uuid.UUID) -> None:
    """Idempotent/resumable per NFR-3: a document not sitting in `VERIFYING`
    has already been verified (or is terminal), so a retry is a no-op."""
    documents = SourceDocumentRepository(db)
    document = documents.get_by_id(document_id)
    if document is None or document.status != DocStatusEnum.VERIFYING:
        return

    with track_stage(db, document.id, PipelineStageEnum.VERIFICATION):
        processing_run = DocumentProcessingRunRepository(db).get_latest_for_document(document.id)
        assert processing_run is not None  # noqa: S101 - VERIFYING implies extraction succeeded

        assert document.storage_path is not None  # noqa: S101 - PASSED docs always have one
        data = get_storage_port().get_object(document.storage_path)
        ocr_text = maybe_recognize_text(data, document.mime_type)
        result = extract(data, mime_type=document.mime_type, ocr_text=ocr_text)

        declared_owner_name = _declared_owner_name(db, document.user_id)
        kimi_evidence = _gather_kimi_evidence(document.id)

        trust_layer_result = run_trust_layer(
            TrustLayerInput(
                source_type=document.source_type,
                rows=result.rows,
                pdf_forensics=result.pdf_forensics,
                statement_start_date=result.statement_start_date,
                statement_end_date=result.statement_end_date,
                declared_owner_name=declared_owner_name,
                detected_account_holder_name=result.detected_account_holder_name,
                kimi_evidence=kimi_evidence,
            )
        )

        model_version = ModelVersionRepository(db).get_active("crediwise-core")
        assert model_version is not None  # noqa: S101 - seeded at bootstrap (T1.7)

        verification_result = DocumentVerificationResult(
            id=uuid.uuid4(),
            source_document_id=document.id,
            processing_run_id=processing_run.id,
            verification_model_version_id=model_version.id,
            metadata_score=trust_layer_result.metadata_score,
            consistency_score=trust_layer_result.consistency_score,
            visual_score=trust_layer_result.visual_score,
            ocr_score=trust_layer_result.ocr_score,
            completeness_score=trust_layer_result.completeness_score,
            ownership_score=trust_layer_result.ownership_score,
            provenance_score=trust_layer_result.provenance_score,
            data_confidence_score=trust_layer_result.data_confidence_score,
            confidence_band=trust_layer_result.band,
            flags_json={
                "reason_codes": [
                    {"code": r.code, "description": r.description}
                    for r in trust_layer_result.reason_codes
                ],
                "recommendation": trust_layer_result.recommendation,
                **trust_layer_result.flags,
            },
            verified_at=datetime.now(UTC),
        )
        DocumentVerificationResultRepository(db).add(verification_result)

        document.status = DocStatusEnum.REVIEW_PENDING
        db.flush()
        audit_service.record(
            db,
            actor_type=ActorTypeEnum.SYSTEM,
            actor_id=None,
            action="document.verification_completed",
            entity_type="source_document",
            entity_id=document.id,
            metadata={
                "data_confidence_score": str(trust_layer_result.data_confidence_score),
                "band": trust_layer_result.band.value,
            },
        )
        db.commit()


def _declared_owner_name(db: Session, user_id: uuid.UUID) -> str | None:
    profile = UserRepository(db).get_profile(user_id)
    return profile.full_name if profile else None


def _gather_kimi_evidence(document_id: uuid.UUID) -> KimiAnomalyEvidence | None:
    """Returns `None` when no local-Kimi port is configured at all (the
    default MVP state) — the engine then reports `ai_signal=DISABLED`,
    distinct from a configured-but-unreachable port (`UNAVAILABLE`, PLAN
    §15.6). Sprint 3 does not render page-region images (see
    `app/integrations/local_ai/README.md`), so a configured port is always
    called with an empty `page_images_base64` list; the local runtime is
    expected to decline to speculate without visual input, but any response
    is still schema-validated before use.
    """
    port = get_document_anomaly_port()
    if port is None:
        return None
    try:
        response = port.analyze(
            DocumentAnomalyRequest(document_ref=str(document_id), page_images_base64=[])
        )
    except Exception:  # noqa: BLE001 - PLAN §15.6: unavailable, never blocks the pipeline
        return KimiAnomalyEvidence(
            available=False, anomaly_probability=Decimal("0"), indicator_count=0
        )
    if response.analysis_status is not AnalysisStatus.COMPLETE:
        return KimiAnomalyEvidence(
            available=False, anomaly_probability=Decimal("0"), indicator_count=0
        )
    return KimiAnomalyEvidence(
        available=True,
        anomaly_probability=Decimal(str(response.anomaly_probability)),
        indicator_count=len(response.indicators),
    )
