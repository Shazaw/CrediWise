"""transactions: persist deterministic duplicate-row signal

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("transactions", "is_duplicate", server_default=None)


def downgrade() -> None:
    op.drop_column("transactions", "is_duplicate")
