"""Persistence for `document_processing_runs` (PLAN §10.1 — no business rules)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_processing_run import DocumentProcessingRun


class DocumentProcessingRunRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, run: DocumentProcessingRun) -> DocumentProcessingRun:
        self._db.add(run)
        self._db.flush()
        return run

    def get_latest_for_document(
        self, source_document_id: uuid.UUID
    ) -> DocumentProcessingRun | None:
        stmt = (
            select(DocumentProcessingRun)
            .where(
                DocumentProcessingRun.source_document_id == source_document_id,
                DocumentProcessingRun.deleted_at.is_(None),
            )
            .order_by(DocumentProcessingRun.started_at.desc())
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none()
