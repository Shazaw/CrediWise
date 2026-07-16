"""Refresh token store (PLAN §18.1 — server-side hashed, revocable).

Not enumerated in PLAN §11.3's table catalogue; added here to implement the
already-documented §18.1 decision ("Refresh tokens are stored server-side
(hashed) so they can be revoked"). PLAN.md §11.3 is updated in the same PR
per §24.11.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CHAR, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    replaced_by_token_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("refresh_tokens.id", ondelete="RESTRICT"), nullable=True
    )

    @property
    def is_active(self) -> bool:
        now = datetime.now(UTC)
        return self.revoked_at is None and self.expires_at > now and self.deleted_at is None
