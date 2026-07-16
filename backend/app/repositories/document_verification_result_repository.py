"""Persistence for `document_verification_results` (PLAN §10.1 — no business rules)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_verification_result import DocumentVerificationResult


class DocumentVerificationResultRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, result: DocumentVerificationResult) -> DocumentVerificationResult:
        self._db.add(result)
        self._db.flush()
        return result

    def get_latest_for_document(
        self, source_document_id: uuid.UUID
    ) -> DocumentVerificationResult | None:
        stmt = (
            select(DocumentVerificationResult)
            .where(
                DocumentVerificationResult.source_document_id == source_document_id,
                DocumentVerificationResult.deleted_at.is_(None),
            )
            .order_by(DocumentVerificationResult.verified_at.desc())
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none()
