"""User-flagged extraction/category/ownership disputes (PLAN §11.3
`corrections`; FR-14 AC1).

PLAN §7.13 tags the full `corrections`/appeal *table* as POST-MVP, but FR-14
and Sprint 3's T3.6 (`POST /documents/{id}/review`) are explicit MVP golden-path
scope (§1.6 step 5: "flags obvious extraction/category/internal-transfer
errors without overwriting raw evidence"). This is the Sprint 3 gap-fill
(PLAN §24.11): the minimal `corrections` shape from §11.3 is brought forward
to back the MVP review flow now; the full appeal/dispute workflow
(`assessment_id` linkage, `POST /assessments/{id}/appeals`) remains
POST-MVP. `payload_json` holds `{raw_extracted_value, system_normalized_value,
user_proposed_value}` per FR-14 AC1 — raw evidence in `transactions`/
`document_processing_runs` is never overwritten by a correction.
"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Correction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "corrections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=True
    )
    correction_type: Mapped[str] = mapped_column(Text(), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, default=dict)
    status: Mapped[str] = mapped_column(Text(), nullable=False, default="PENDING")
