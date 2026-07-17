"""Persistence for `assessment_reason_codes` (PLAN §10.1 — no business rules)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment_reason_code import AssessmentReasonCode


class AssessmentReasonCodeRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add_all(self, codes: list[AssessmentReasonCode]) -> list[AssessmentReasonCode]:
        self._db.add_all(codes)
        self._db.flush()
        return codes

    def list_for_assessment(self, assessment_id: uuid.UUID) -> list[AssessmentReasonCode]:
        stmt = select(AssessmentReasonCode).where(
            AssessmentReasonCode.assessment_id == assessment_id,
            AssessmentReasonCode.deleted_at.is_(None),
        )
        return list(self._db.execute(stmt).scalars().all())
