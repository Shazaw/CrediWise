"""doc_status_enum: add REVIEW_PENDING

Sprint 3 gap-fill (PLAN §24.11): PLAN §8.2's state diagram requires
`VERIFYING -> REVIEW_PENDING -> NORMALIZING` but Appendix A's `doc_status_enum`
list omits `REVIEW_PENDING` (same class of gap as Sprint 2's
`VALIDATION_FAILED`/`DUPLICATE_REUSED`, migration 0003). `doc_status_enum`
itself was created by migration 0003 (already applied/shared), so this is a
new migration rather than an edit to 0003 (PLAN §24.6: "never edit a merged
migration").

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_VALUES = (
    "UPLOADED",
    "SECURITY_CHECK",
    "REJECTED_SECURITY",
    "VALIDATION_FAILED",
    "DUPLICATE_REUSED",
    "EXTRACTING",
    "UNSUPPORTED_FORMAT",
    "VERIFYING",
    "NORMALIZING",
    "ANALYZING",
    "HUMAN_REVIEW",
    "COMPLETE",
)


def upgrade() -> None:
    op.execute("ALTER TYPE doc_status_enum ADD VALUE IF NOT EXISTS 'REVIEW_PENDING'")


def downgrade() -> None:
    # Postgres has no `DROP VALUE`; recreate the type without REVIEW_PENDING
    # (safe in local/CI where this runs against an empty schema before any
    # document rows exist — PLAN §11.4 forward-only rule still applies to
    # shared/staging/prod environments).
    op.execute("ALTER TABLE source_documents ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE doc_status_enum RENAME TO doc_status_enum_old")
    new_enum = postgresql.ENUM(*_OLD_VALUES, name="doc_status_enum")
    new_enum.create(op.get_bind(), checkfirst=False)
    op.execute(
        "ALTER TABLE source_documents ALTER COLUMN status TYPE doc_status_enum "
        "USING status::text::doc_status_enum"
    )
    op.execute("ALTER TABLE source_documents ALTER COLUMN status SET DEFAULT 'UPLOADED'")
    op.execute("DROP TYPE doc_status_enum_old")
