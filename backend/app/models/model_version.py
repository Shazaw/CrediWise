"""Model governance registry (PLAN §11.3 `model_versions`, §19.2).

Real deterministic-engine weights land starting Sprint 3+; this table plus a
bootstrap ACTIVE row exist from Sprint 1 so `assessments.model_version_id`
has a stable FK target from day one (T1.7).
"""

from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ModelStatusEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class ModelVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_versions"

    model_name: Mapped[str] = mapped_column(Text(), nullable=False)
    version: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[ModelStatusEnum] = mapped_column(
        sa_enum(ModelStatusEnum, "model_status_enum"),
        nullable=False,
        default=ModelStatusEnum.DRAFT,
    )
    config_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    training_data_reference: Mapped[str | None] = mapped_column(Text(), nullable=True)
    validation_metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(nullable=True)
