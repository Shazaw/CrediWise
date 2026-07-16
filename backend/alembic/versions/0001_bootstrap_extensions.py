"""bootstrap: enable pgcrypto for gen_random_uuid()

Every table's primary key uses ``id UUID DEFAULT gen_random_uuid()``
(PLAN §11.1). This bootstrap migration enables the Postgres extension that
default depends on, ahead of any domain tables (added starting Sprint 1).

Revision ID: 0001
Revises:
Create Date: 2026-07-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')


def downgrade() -> None:
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
