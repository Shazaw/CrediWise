"""Complete Cycle 6 temporal shock and offer safety persistence.

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "shock_scenarios",
        sa.Column("projection_points_json", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "shock_scenarios",
        sa.Column("required_buffer_breached", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "offer_assessments",
        sa.Column(
            "remaining_essential_expense_coverage",
            sa.BigInteger(),
            nullable=True,
        ),
    )
    op.add_column(
        "offer_assessments",
        sa.Column(
            "remaining_essential_expense_coverage_ratio",
            sa.Numeric(8, 2),
            nullable=True,
        ),
    )
    op.add_column(
        "offer_assessments",
        sa.Column("refinancing_dependency", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "offer_assessments",
        sa.Column(
            "reason_codes_json",
            postgresql.JSONB(),
            nullable=True,
        ),
    )
    op.add_column(
        "lender_offers",
        sa.Column("canonical_template_key", sa.Text(), nullable=True),
    )
    op.create_index(
        "uq_lender_offers_canonical_simulated_set",
        "lender_offers",
        ["assessment_id", "canonical_template_key"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND offer_source = 'SIMULATED' "
            "AND canonical_template_key IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_lender_offers_canonical_simulated_set", table_name="lender_offers")
    op.drop_column("lender_offers", "canonical_template_key")
    op.drop_column("offer_assessments", "reason_codes_json")
    op.drop_column("offer_assessments", "refinancing_dependency")
    op.drop_column("offer_assessments", "remaining_essential_expense_coverage_ratio")
    op.drop_column("offer_assessments", "remaining_essential_expense_coverage")
    op.drop_column("shock_scenarios", "required_buffer_breached")
    op.drop_column("shock_scenarios", "projection_points_json")
