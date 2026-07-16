"""Append-only audit trail (PLAN §11.3, §18.1 threat model, FR-15).

No `updated_at`/`deleted_at` — audit rows are immutable by design.
Application code must never UPDATE or DELETE a row here (DB-level role
grants enforcing this are production hardening, PLAN Sprint 10).
"""

import uuid
from typing import Any

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ActorTypeEnum
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.sa_enum import sa_enum


class AuditLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "audit_logs"

    actor_type: Mapped[ActorTypeEnum] = mapped_column(
        sa_enum(ActorTypeEnum, "actor_enum"), nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(Text(), nullable=False)
    entity_type: Mapped[str] = mapped_column(Text(), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
