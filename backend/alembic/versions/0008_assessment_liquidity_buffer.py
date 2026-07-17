"""assessments: persist deterministic required liquidity buffer

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("required_liquidity_buffer", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessments", "required_liquidity_buffer")
