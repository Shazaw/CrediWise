"""Persistence for `source_documents` (PLAN §10.1 — no business rules here)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.source_document import SourceDocument


class SourceDocumentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, document_id: uuid.UUID) -> SourceDocument | None:
        stmt = select(SourceDocument).where(
            SourceDocument.id == document_id, SourceDocument.deleted_at.is_(None)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def get_by_user_and_hash(self, user_id: uuid.UUID, file_hash: str) -> SourceDocument | None:
        """FR-3 AC3 dedup lookup — same user, same SHA-256."""
        stmt = select(SourceDocument).where(
            SourceDocument.user_id == user_id,
            SourceDocument.file_hash == file_hash,
            SourceDocument.deleted_at.is_(None),
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def add(self, document: SourceDocument) -> SourceDocument:
        self._db.add(document)
        self._db.flush()
        return document
