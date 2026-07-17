"""shocks, offers & full dashboard: shock_scenarios, lenders, lender_offers,
offer_assessments

Sprint 5 schema (PLAN §11.3, §25 Sprint 5, T5.1-T5.4). `shock_type_enum`,
`afford_enum`, `offer_source_enum`, `amortization_enum`, and `offer_rating_enum`
member sets are Sprint 5 gap-fills (PLAN §24.11) -- see `app/models/enums.py`
and PLAN.md §11.3/Appendix A. `reg_status_enum` extends PLAN §11.3's
documented two-member set with a third, `SIMULATED_REGULATED_PROVIDER`
(FR-11 AC5, ADR-016). `band_enum` and `freq_enum` are reused as-is (no new
type) for `offer_assessments.shock_resilience_status` and
`lender_offers.frequency` respectively.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_shock_type_enum = postgresql.ENUM(
    "INCOME_DROP_10",
    "INCOME_DROP_20",
    "INCOME_DROP_30",
    "DELAYED_INCOME",
    "EMERGENCY_EXPENSE",
    "INCOME_SOURCE_LOSS",
    "WEAKEST_MONTH_REPLAY",
    "CUSTOM",
    name="shock_type_enum",
    create_type=False,
)
_afford_enum = postgresql.ENUM(
    "SURVIVABLE", "STRAINED", "DEFICIT", name="afford_enum", create_type=False
)
_offer_source_enum = postgresql.ENUM(
    "SIMULATED",
    "LENDER_API",
    "MANUAL_LENDER_ENTRY",
    name="offer_source_enum",
    create_type=False,
)
_amortization_enum = postgresql.ENUM(
    "FLAT", "REDUCING_BALANCE", "FIXED_SCHEDULE", name="amortization_enum", create_type=False
)
_reg_status_enum = postgresql.ENUM(
    "REGULATED",
    "UNLISTED",
    "SIMULATED_REGULATED_PROVIDER",
    name="reg_status_enum",
    create_type=False,
)
_offer_rating_enum = postgresql.ENUM(
    "GOOD", "FAIR", "POOR", name="offer_rating_enum", create_type=False
)
_band_enum = postgresql.ENUM("HIGH", "MEDIUM", "LOW", name="band_enum", create_type=False)
_freq_enum = postgresql.ENUM("MONTHLY", "BIWEEKLY", "WEEKLY", name="freq_enum", create_type=False)

_NEW_ENUMS = [
    _shock_type_enum,
    _afford_enum,
    _offer_source_enum,
    _amortization_enum,
    _reg_status_enum,
    _offer_rating_enum,
]

_TRIGGERED_TABLES = ["shock_scenarios", "lenders", "lender_offers", "offer_assessments"]


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in _NEW_ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "shock_scenarios",
        *_timestamp_columns(),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("scenario_type", _shock_type_enum, nullable=False),
        sa.Column(
            "scenario_parameters_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("projected_cash_flow", sa.BigInteger(), nullable=False),
        sa.Column("minimum_projected_balance", sa.BigInteger(), nullable=False),
        sa.Column("deficit_amount", sa.BigInteger(), nullable=False),
        sa.Column("affordability_status", _afford_enum, nullable=False),
        sa.Column("resilience_score_contribution", sa.Numeric(6, 2), nullable=False),
    )
    op.create_index(
        "ix_shock_scenarios_assessment_type",
        "shock_scenarios",
        ["assessment_id", "scenario_type"],
    )

    op.create_table(
        "lenders",
        *_timestamp_columns(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("regulatory_status", _reg_status_enum, nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "lender_offers",
        *_timestamp_columns(),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "lender_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lenders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("offer_source", _offer_source_enum, nullable=False),
        sa.Column("principal_amount", sa.BigInteger(), nullable=False),
        sa.Column("net_disbursed_amount", sa.BigInteger(), nullable=False),
        sa.Column("instalment_amount", sa.BigInteger(), nullable=False),
        sa.Column("tenor_months", sa.Integer(), nullable=False),
        sa.Column("amortization_method", _amortization_enum, nullable=False),
        sa.Column("nominal_rate", sa.Numeric(6, 4), nullable=True),
        sa.Column("effective_annual_rate", sa.Numeric(6, 4), nullable=True),
        sa.Column("interest_amount", sa.BigInteger(), nullable=False),
        sa.Column("upfront_fee", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("financed_fee", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("service_fee", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("admin_fee", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_repayment", sa.BigInteger(), nullable=False),
        sa.Column("late_penalty_terms_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "payment_schedule_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("due_date", sa.Integer(), nullable=False),
        sa.Column("frequency", _freq_enum, nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lender_offers_assessment", "lender_offers", ["assessment_id"])

    op.create_table(
        "offer_assessments",
        *_timestamp_columns(),
        sa.Column(
            "lender_offer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lender_offers.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("safe_offer_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("affordability_status", _afford_enum, nullable=False),
        sa.Column("shock_resilience_status", _band_enum, nullable=False),
        sa.Column("total_cost_status", _offer_rating_enum, nullable=False),
        sa.Column("timing_status", _offer_rating_enum, nullable=False),
        sa.Column(
            "warning_flags_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
    )

    for table_name in _TRIGGERED_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_updated_at BEFORE UPDATE ON {table_name} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    op.drop_table("offer_assessments")
    op.drop_table("lender_offers")
    op.drop_table("lenders")
    op.drop_table("shock_scenarios")

    bind = op.get_bind()
    for enum_type in reversed(_NEW_ENUMS):
        enum_type.drop(bind, checkfirst=True)
