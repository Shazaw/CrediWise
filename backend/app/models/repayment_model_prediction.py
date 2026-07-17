"""Append-only shadow repayment-model evidence tied to immutable assessment lineage."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import CHAR, CheckConstraint, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import (
    BandEnum,
    RepaymentModelModeEnum,
    RepaymentPredictionStatusEnum,
)
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class RepaymentModelPrediction(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "repayment_model_predictions"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "model_version_id",
            "mode",
            name="uq_repayment_prediction_assessment_model_mode",
        ),
        CheckConstraint(
            "raw_probability IS NULL OR (raw_probability >= 0 AND raw_probability <= 1)",
            name="ck_repayment_prediction_raw_probability",
        ),
        CheckConstraint(
            "calibrated_probability IS NULL OR "
            "(calibrated_probability >= 0 AND calibrated_probability <= 1)",
            name="ck_repayment_prediction_calibrated_probability",
        ),
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False
    )
    mode: Mapped[RepaymentModelModeEnum] = mapped_column(
        sa_enum(RepaymentModelModeEnum, "repayment_model_mode_enum"), nullable=False
    )
    status: Mapped[RepaymentPredictionStatusEnum] = mapped_column(
        sa_enum(RepaymentPredictionStatusEnum, "repayment_prediction_status_enum"),
        nullable=False,
    )
    feature_schema_version: Mapped[str] = mapped_column(Text(), nullable=False)
    feature_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    feature_vector_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    artifact_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    raw_probability: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    calibrated_probability: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    model_confidence: Mapped[BandEnum | None] = mapped_column(
        sa_enum(BandEnum, "band_enum"), nullable=True
    )
    reason_codes_json: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False, default=list)
    out_of_domain_features_json: Mapped[list[Any]] = mapped_column(
        JSONB(), nullable=False, default=list
    )
    failure_code: Mapped[str | None] = mapped_column(Text(), nullable=True)
