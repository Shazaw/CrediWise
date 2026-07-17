"""Shared `pipeline_stage_runs` instrumentation (PLAN §11.3, NFR-3; T3.2).

A thin context manager so `extraction_service.run_extraction`,
`verification_service.run_verification`, and `normalization_service
.run_normalization` each record one attempt row per invocation — start
time, attempt number, and either a `SUCCEEDED` or `FAILED` outcome —
without duplicating the bookkeeping in each service. Document-level
idempotency (skipping a stage whose document status has already moved on)
still lives in each service's own entry guard; this is purely the
observability/attempt-history record NFR-3 asks for.

`track_assessment_stage` is the assessment-scoped sibling added in Sprint 4
for `assessment_service.run_assessment_analysis` (§11.3 `pipeline_stage_runs`
note: "Sprint 4's migration adds `assessment_id`" -- the `ANALYSIS` stage is
the reason why).
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.enums import PipelineStageEnum, StageStatusEnum
from app.models.pipeline_stage_run import PipelineStageRun
from app.repositories.pipeline_stage_run_repository import PipelineStageRunRepository

_WORKER_VERSION = "1.0.0"
_MAX_ERROR_MESSAGE_LENGTH = 500


@contextmanager
def track_stage(db: Session, document_id: uuid.UUID, stage: PipelineStageEnum) -> Iterator[None]:
    repo = PipelineStageRunRepository(db)
    attempt_number = repo.count_attempts(document_id, stage) + 1
    run = PipelineStageRun(
        id=uuid.uuid4(),
        source_document_id=document_id,
        stage=stage,
        status=StageStatusEnum.RUNNING,
        attempt_number=attempt_number,
        worker_version=_WORKER_VERSION,
        started_at=datetime.now(UTC),
    )
    repo.add(run)
    db.flush()
    try:
        yield
    except Exception as exc:
        run.status = StageStatusEnum.FAILED
        run.completed_at = datetime.now(UTC)
        run.error_code = type(exc).__name__
        run.sanitized_error_message = str(exc)[:_MAX_ERROR_MESSAGE_LENGTH]
        db.flush()
        raise
    else:
        run.status = StageStatusEnum.SUCCEEDED
        run.completed_at = datetime.now(UTC)
        db.flush()


@contextmanager
def track_assessment_stage(
    db: Session, assessment_id: uuid.UUID, stage: PipelineStageEnum
) -> Iterator[None]:
    repo = PipelineStageRunRepository(db)
    attempt_number = repo.count_attempts_for_assessment(assessment_id, stage) + 1
    run = PipelineStageRun(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        stage=stage,
        status=StageStatusEnum.RUNNING,
        attempt_number=attempt_number,
        worker_version=_WORKER_VERSION,
        started_at=datetime.now(UTC),
    )
    repo.add(run)
    db.flush()
    try:
        yield
    except Exception as exc:
        run.status = StageStatusEnum.FAILED
        run.completed_at = datetime.now(UTC)
        run.error_code = type(exc).__name__
        run.sanitized_error_message = str(exc)[:_MAX_ERROR_MESSAGE_LENGTH]
        db.flush()
        raise
    else:
        run.status = StageStatusEnum.SUCCEEDED
        run.completed_at = datetime.now(UTC)
        db.flush()
