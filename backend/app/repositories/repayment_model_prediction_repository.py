"""Persistence for append-only repayment-model shadow predictions."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repayment_model_prediction import RepaymentModelPrediction


class RepaymentModelPredictionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, prediction: RepaymentModelPrediction) -> RepaymentModelPrediction:
        self._db.add(prediction)
        self._db.flush()
        return prediction

    def get_for_assessment(self, assessment_id: uuid.UUID) -> RepaymentModelPrediction | None:
        stmt = (
            select(RepaymentModelPrediction)
            .where(RepaymentModelPrediction.assessment_id == assessment_id)
            .order_by(RepaymentModelPrediction.created_at.desc())
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def get_exact(
        self, assessment_id: uuid.UUID, model_version_id: uuid.UUID
    ) -> RepaymentModelPrediction | None:
        stmt = select(RepaymentModelPrediction).where(
            RepaymentModelPrediction.assessment_id == assessment_id,
            RepaymentModelPrediction.model_version_id == model_version_id,
        )
        return self._db.execute(stmt).scalar_one_or_none()
