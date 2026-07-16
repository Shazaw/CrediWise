"""Persistence for `model_versions` (PLAN §10.1 — no business rules; §19.2)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ModelStatusEnum
from app.models.model_version import ModelVersion


class ModelVersionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_active(self, model_name: str) -> ModelVersion | None:
        stmt = select(ModelVersion).where(
            ModelVersion.model_name == model_name,
            ModelVersion.status == ModelStatusEnum.ACTIVE,
            ModelVersion.deleted_at.is_(None),
        )
        return self._db.execute(stmt).scalar_one_or_none()
