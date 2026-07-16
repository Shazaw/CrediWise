"""Persistence for `pipeline_stage_runs` (PLAN §10.1 — no business rules; NFR-3)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import PipelineStageEnum
from app.models.pipeline_stage_run import PipelineStageRun


class PipelineStageRunRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, run: PipelineStageRun) -> PipelineStageRun:
        self._db.add(run)
        self._db.flush()
        return run

    def count_attempts(self, source_document_id: uuid.UUID, stage: PipelineStageEnum) -> int:
        stmt = select(PipelineStageRun).where(
            PipelineStageRun.source_document_id == source_document_id,
            PipelineStageRun.stage == stage,
        )
        return len(list(self._db.execute(stmt).scalars().all()))
