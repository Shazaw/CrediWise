"""Persistence for the `assessments` aggregate (PLAN §10.1 — no business
rules): the assessment row itself plus its document/transaction lineage
junctions and immutable input snapshot -- all child entities of the same
aggregate root (PLAN §10.1 "one repository per aggregate")."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.assessment_document import AssessmentDocument
from app.models.assessment_input_snapshot import AssessmentInputSnapshot
from app.models.assessment_transaction import AssessmentTransaction


class AssessmentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, assessment: Assessment) -> Assessment:
        self._db.add(assessment)
        self._db.flush()
        return assessment

    def get_by_id(self, assessment_id: uuid.UUID) -> Assessment | None:
        stmt = select(Assessment).where(
            Assessment.id == assessment_id, Assessment.deleted_at.is_(None)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_for_user(self, user_id: uuid.UUID) -> list[Assessment]:
        stmt = (
            select(Assessment)
            .where(Assessment.user_id == user_id, Assessment.deleted_at.is_(None))
            .order_by(Assessment.created_at.desc())
        )
        return list(self._db.execute(stmt).scalars().all())

    def add_document_links(self, links: list[AssessmentDocument]) -> list[AssessmentDocument]:
        self._db.add_all(links)
        self._db.flush()
        return links

    def add_transaction_links(
        self, links: list[AssessmentTransaction]
    ) -> list[AssessmentTransaction]:
        self._db.add_all(links)
        self._db.flush()
        return links

    def get_document_links(self, assessment_id: uuid.UUID) -> list[AssessmentDocument]:
        stmt = select(AssessmentDocument).where(
            AssessmentDocument.assessment_id == assessment_id,
            AssessmentDocument.deleted_at.is_(None),
        )
        return list(self._db.execute(stmt).scalars().all())

    def get_transaction_links(self, assessment_id: uuid.UUID) -> list[AssessmentTransaction]:
        stmt = select(AssessmentTransaction).where(
            AssessmentTransaction.assessment_id == assessment_id,
            AssessmentTransaction.deleted_at.is_(None),
        )
        return list(self._db.execute(stmt).scalars().all())

    def add_snapshot(self, snapshot: AssessmentInputSnapshot) -> AssessmentInputSnapshot:
        self._db.add(snapshot)
        self._db.flush()
        return snapshot

    def get_snapshot(self, assessment_id: uuid.UUID) -> AssessmentInputSnapshot | None:
        stmt = select(AssessmentInputSnapshot).where(
            AssessmentInputSnapshot.assessment_id == assessment_id,
            AssessmentInputSnapshot.deleted_at.is_(None),
        )
        return self._db.execute(stmt).scalar_one_or_none()
