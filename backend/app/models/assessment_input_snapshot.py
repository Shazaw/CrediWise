"""Immutable reproducibility package, 1:1 per assessment (PLAN §11.3
`assessment_input_snapshots`; FR-18, NFR-17).

No service ever calls `UPDATE` on this row after creation (PLAN §11.3: "No
UPDATE after assessment starts; a changed input requires a new assessment").
`offer_terms_json`/`simulation_parameters_json` stay empty until Sprint 5's
Shock/Offer engines populate them for the same row.
"""

import uuid
from typing import Any

from sqlalchemy import CHAR, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AssessmentInputSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_input_snapshots"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    snapshot_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    normalized_input_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, default=dict
    )
    document_refs_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, default=dict
    )
    transaction_refs_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, default=dict
    )
    accepted_corrections_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, default=dict
    )
    parser_versions_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, default=dict
    )
    categorizer_version: Mapped[str] = mapped_column(Text(), nullable=False)
    engine_config_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    simulation_parameters_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, default=dict
    )
    offer_terms_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, default=dict)
