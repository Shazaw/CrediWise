"""Append-only Trust-Layer output per processing run (PLAN §11.3
`document_verification_results`; §5.2, FR-5).

The 7 named sub-scores mirror `TrustLayerEngine`'s output 1:1 (PLAN §15.1,
§5.2's weighted-model table). `verification_model_version_id` stamps which
`model_versions` row (weights/thresholds) produced this result — required
for reproducibility (PLAN §15.4, NFR-17, §19.2).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import BandEnum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum

_SCORE = Numeric(6, 2)


class DocumentVerificationResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_verification_results"

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False
    )
    processing_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_processing_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    verification_model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False
    )
    supersedes_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_verification_results.id", ondelete="RESTRICT"),
        nullable=True,
    )
    metadata_score: Mapped[Decimal] = mapped_column(_SCORE, nullable=False)
    consistency_score: Mapped[Decimal] = mapped_column(_SCORE, nullable=False)
    visual_score: Mapped[Decimal] = mapped_column(_SCORE, nullable=False)
    ocr_score: Mapped[Decimal] = mapped_column(_SCORE, nullable=False)
    completeness_score: Mapped[Decimal] = mapped_column(_SCORE, nullable=False)
    ownership_score: Mapped[Decimal] = mapped_column(_SCORE, nullable=False)
    provenance_score: Mapped[Decimal] = mapped_column(_SCORE, nullable=False)
    data_confidence_score: Mapped[Decimal] = mapped_column(_SCORE, nullable=False)
    confidence_band: Mapped[BandEnum] = mapped_column(
        sa_enum(BandEnum, "band_enum"), nullable=False
    )
    flags_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, default=dict)
    verified_at: Mapped[datetime] = mapped_column(nullable=False)
