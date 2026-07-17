"""twin, risk & safe borrowing: financing_needs, assessments, assessment
lineage/snapshot tables, financial_profiles, monthly_cash_flow_snapshots,
income_sources, recurring_series, cash_flow_events, assessment_reason_codes;
pipeline_stage_runs.assessment_id; pipeline_stage_enum NORMALIZATION/ANALYSIS

Sprint 4 schema (PLAN §11.3, §25 Sprint 4, T4.1-T4.5). `urgency_enum`,
`income_source_enum`, `recurring_type_enum`, `cash_event_enum`,
`coverage_enum`, `inclusion_enum`, and `severity_enum` member sets are
Sprint 4 gap-fills (PLAN §24.11) — see `app/models/enums.py` and
PLAN.md §11.3/Appendix A. `pipeline_stage_enum` gains `NORMALIZATION`/
`ANALYSIS` via `ALTER TYPE ... ADD VALUE`, the same pattern migration 0005
used for `doc_status_enum.REVIEW_PENDING` (that type was created by an
already-applied migration, so §24.6 forbids editing it in place).

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_purpose_enum = postgresql.ENUM(
    "MEDICAL",
    "EDUCATION",
    "HOUSEHOLD_EMERGENCY",
    "PRODUCTIVE_BUSINESS",
    "EQUIPMENT",
    "WORKING_CAPITAL",
    "VEHICLE_DEVICE_REPAIR",
    name="purpose_enum",
    create_type=False,
)
_urgency_enum = postgresql.ENUM("LOW", "MEDIUM", "HIGH", name="urgency_enum", create_type=False)
_assessment_status_enum = postgresql.ENUM(
    "PENDING",
    "ANALYZING",
    "COMPLETE",
    "FAILED",
    "HUMAN_REVIEW",
    name="assessment_status_enum",
    create_type=False,
)
_risk_band_enum = postgresql.ENUM(
    "A", "B", "C", "D", "INSUFFICIENT_DATA", name="risk_band_enum", create_type=False
)
_freq_enum = postgresql.ENUM(
    "MONTHLY", "BIWEEKLY", "WEEKLY", name="freq_enum", create_type=False
)
_income_source_enum = postgresql.ENUM(
    "SALARY",
    "BUSINESS_REVENUE",
    "FREELANCE",
    "QRIS_SETTLEMENT",
    "MARKETPLACE_SETTLEMENT",
    "OTHER",
    name="income_source_enum",
    create_type=False,
)
_recurring_type_enum = postgresql.ENUM(
    "INCOME", "EXPENSE", "DEBT_PAYMENT", name="recurring_type_enum", create_type=False
)
_cash_event_enum = postgresql.ENUM(
    "INCOME", "ESSENTIAL_EXPENSE", name="cash_event_enum", create_type=False
)
_coverage_enum = postgresql.ENUM(
    "SUFFICIENT", "LOW_COVERAGE", name="coverage_enum", create_type=False
)
_inclusion_enum = postgresql.ENUM(
    "INCLUDED", "EXCLUDED", name="inclusion_enum", create_type=False
)
_reason_type_enum = postgresql.ENUM(
    "POSITIVE", "RISK", "DATA_QUALITY", "OFFER", name="reason_type_enum", create_type=False
)
_severity_enum = postgresql.ENUM(
    "INFO", "LOW", "MEDIUM", "HIGH", name="severity_enum", create_type=False
)
_band_enum = postgresql.ENUM("HIGH", "MEDIUM", "LOW", name="band_enum", create_type=False)
_dir_enum = postgresql.ENUM("CREDIT", "DEBIT", name="dir_enum", create_type=False)

_NEW_ENUMS = [
    _purpose_enum,
    _urgency_enum,
    _assessment_status_enum,
    _risk_band_enum,
    _freq_enum,
    _income_source_enum,
    _recurring_type_enum,
    _cash_event_enum,
    _coverage_enum,
    _inclusion_enum,
    _reason_type_enum,
    _severity_enum,
]

_TRIGGERED_TABLES = [
    "financing_needs",
    "assessments",
    "assessment_documents",
    "assessment_transactions",
    "assessment_input_snapshots",
    "financial_profiles",
    "monthly_cash_flow_snapshots",
    "income_sources",
    "recurring_series",
    "cash_flow_events",
    "assessment_reason_codes",
]


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
    op.execute("ALTER TYPE pipeline_stage_enum ADD VALUE IF NOT EXISTS 'NORMALIZATION'")
    op.execute("ALTER TYPE pipeline_stage_enum ADD VALUE IF NOT EXISTS 'ANALYSIS'")

    bind = op.get_bind()
    for enum_type in _NEW_ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "financing_needs",
        *_timestamp_columns(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("requested_amount", sa.BigInteger(), nullable=False),
        sa.Column("purpose", _purpose_enum, nullable=False),
        sa.Column("preferred_tenor_months", sa.Integer(), nullable=False),
        sa.Column("urgency", _urgency_enum, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "requested_amount > 0 AND requested_amount <= 1000000000",
            name="ck_financing_needs_requested_amount_range",
        ),
        sa.CheckConstraint(
            "preferred_tenor_months BETWEEN 1 AND 36",
            name="ck_financing_needs_tenor_range",
        ),
    )
    op.create_index("ix_financing_needs_user", "financing_needs", ["user_id"])

    op.create_table(
        "assessments",
        *_timestamp_columns(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "financing_need_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("financing_needs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("data_confidence_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("indicative_risk_band", _risk_band_enum, nullable=True),
        sa.Column("model_confidence", _band_enum, nullable=True),
        sa.Column("shock_resilience_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("safe_loan_amount", sa.BigInteger(), nullable=True),
        sa.Column("maximum_safe_instalment", sa.BigInteger(), nullable=True),
        sa.Column("recommended_tenor_months", sa.Integer(), nullable=True),
        sa.Column("recommended_due_date_start", sa.Integer(), nullable=True),
        sa.Column("recommended_due_date_end", sa.Integer(), nullable=True),
        sa.Column("recommended_frequency", _freq_enum, nullable=True),
        sa.Column("status", _assessment_status_enum, nullable=False, server_default="PENDING"),
    )
    op.create_index(
        "ix_assessments_user_created", "assessments", ["user_id", sa.text("created_at DESC")]
    )
    op.create_index("ix_assessments_status", "assessments", ["status"])

    op.create_table(
        "assessment_documents",
        *_timestamp_columns(),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "processing_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_processing_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "verification_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_verification_results.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("inclusion_status", _inclusion_enum, nullable=False, server_default="INCLUDED"),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "assessment_id",
            "source_document_id",
            "processing_run_id",
            name="uq_assessment_documents_assessment_document_run",
        ),
    )

    op.create_table(
        "assessment_transactions",
        *_timestamp_columns(),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("inclusion_status", _inclusion_enum, nullable=False, server_default="INCLUDED"),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "assessment_id", "transaction_id", name="uq_assessment_transactions_assessment_transaction"
        ),
    )

    op.create_table(
        "assessment_input_snapshots",
        *_timestamp_columns(),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("snapshot_hash", sa.CHAR(64), nullable=False),
        sa.Column(
            "normalized_input_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "document_refs_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "transaction_refs_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "accepted_corrections_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "parser_versions_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("categorizer_version", sa.Text(), nullable=False),
        sa.Column("engine_config_hash", sa.CHAR(64), nullable=False),
        sa.Column(
            "simulation_parameters_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "offer_terms_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.create_table(
        "financial_profiles",
        *_timestamp_columns(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("average_income", sa.BigInteger(), nullable=False),
        sa.Column("median_income", sa.BigInteger(), nullable=False),
        sa.Column("income_volatility", sa.Numeric(6, 4), nullable=False),
        sa.Column("essential_expenses", sa.BigInteger(), nullable=False),
        sa.Column("discretionary_expenses", sa.BigInteger(), nullable=False),
        sa.Column("existing_debt", sa.BigInteger(), nullable=False),
        sa.Column("average_free_cash_flow", sa.BigInteger(), nullable=False),
        sa.Column("minimum_balance", sa.BigInteger(), nullable=False),
        sa.Column("positive_cash_flow_ratio", sa.Numeric(6, 4), nullable=False),
        sa.Column("weakest_month_cash_flow", sa.BigInteger(), nullable=False),
        sa.Column("savings_buffer", sa.BigInteger(), nullable=False),
        sa.Column("months_covered", sa.Integer(), nullable=False),
        sa.Column("coverage_flag", _coverage_enum, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "monthly_cash_flow_snapshots",
        *_timestamp_columns(),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("year_month", sa.Date(), nullable=False),
        sa.Column("personal_income", sa.BigInteger(), nullable=False),
        sa.Column("business_income", sa.BigInteger(), nullable=False),
        sa.Column("essential_expenses", sa.BigInteger(), nullable=False),
        sa.Column("discretionary_expenses", sa.BigInteger(), nullable=False),
        sa.Column("business_expenses", sa.BigInteger(), nullable=False),
        sa.Column("debt_service", sa.BigInteger(), nullable=False),
        sa.Column("opening_balance", sa.BigInteger(), nullable=False),
        sa.Column("minimum_balance", sa.BigInteger(), nullable=False),
        sa.Column("closing_balance", sa.BigInteger(), nullable=False),
        sa.Column("net_cash_flow", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint(
            "assessment_id", "year_month", name="uq_monthly_cash_flow_snapshots_assessment_month"
        ),
    )

    op.create_table(
        "income_sources",
        *_timestamp_columns(),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("source_type", _income_source_enum, nullable=False),
        sa.Column("average_amount", sa.BigInteger(), nullable=False),
        sa.Column("frequency", _freq_enum, nullable=False),
        sa.Column("volatility", sa.Numeric(6, 4), nullable=False),
        sa.Column("concentration_ratio", sa.Numeric(6, 4), nullable=False),
        sa.Column("dominant_arrival_day", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Numeric(6, 4), nullable=False),
    )
    op.create_index("ix_income_sources_assessment", "income_sources", ["assessment_id"])

    op.create_table(
        "recurring_series",
        *_timestamp_columns(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "financial_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("financial_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("series_type", _recurring_type_enum, nullable=False),
        sa.Column("normalized_counterparty", sa.Text(), nullable=False),
        sa.Column("median_amount", sa.BigInteger(), nullable=False),
        sa.Column("expected_interval_days", sa.Integer(), nullable=False),
        sa.Column("expected_day_of_month", sa.Integer(), nullable=True),
        sa.Column("regularity_score", sa.Numeric(6, 4), nullable=False),
        sa.Column("confidence", sa.Numeric(6, 4), nullable=False),
    )
    op.create_index(
        "ix_recurring_series_user_account", "recurring_series", ["user_id", "financial_account_id"]
    )

    op.create_table(
        "cash_flow_events",
        *_timestamp_columns(),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("expected_day_of_month", sa.Integer(), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("direction", _dir_enum, nullable=False),
        sa.Column("event_type", _cash_event_enum, nullable=False),
        sa.Column(
            "recurring_series_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recurring_series.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("confidence", sa.Numeric(6, 4), nullable=False),
    )
    op.create_index("ix_cash_flow_events_assessment", "cash_flow_events", ["assessment_id"])

    op.create_table(
        "assessment_reason_codes",
        *_timestamp_columns(),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reason_type", _reason_type_enum, nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", _severity_enum, nullable=False),
        sa.Column(
            "evidence_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )
    op.create_index(
        "ix_assessment_reason_codes_assessment_type",
        "assessment_reason_codes",
        ["assessment_id", "reason_type"],
    )

    op.add_column(
        "pipeline_stage_runs",
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_pipeline_stage_runs_assessment_stage",
        "pipeline_stage_runs",
        ["assessment_id", "stage"],
    )

    for table_name in _TRIGGERED_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_updated_at BEFORE UPDATE ON {table_name} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    op.drop_index("ix_pipeline_stage_runs_assessment_stage", table_name="pipeline_stage_runs")
    op.drop_column("pipeline_stage_runs", "assessment_id")

    op.drop_table("assessment_reason_codes")
    op.drop_table("cash_flow_events")
    op.drop_table("recurring_series")
    op.drop_table("income_sources")
    op.drop_table("monthly_cash_flow_snapshots")
    op.drop_table("financial_profiles")
    op.drop_table("assessment_input_snapshots")
    op.drop_table("assessment_transactions")
    op.drop_table("assessment_documents")
    op.drop_table("assessments")
    op.drop_table("financing_needs")

    bind = op.get_bind()
    for enum_type in reversed(_NEW_ENUMS):
        enum_type.drop(bind, checkfirst=True)

    # Postgres has no `DROP VALUE`; recreate pipeline_stage_enum without
    # NORMALIZATION/ANALYSIS (safe in local/CI against an empty schema, same
    # approach as migration 0005's doc_status_enum downgrade).
    op.execute("ALTER TABLE pipeline_stage_runs ALTER COLUMN stage DROP DEFAULT")
    op.execute("ALTER TYPE pipeline_stage_enum RENAME TO pipeline_stage_enum_old")
    restored = postgresql.ENUM("EXTRACTION", "VERIFICATION", name="pipeline_stage_enum")
    restored.create(bind, checkfirst=False)
    op.execute(
        "ALTER TABLE pipeline_stage_runs ALTER COLUMN stage TYPE pipeline_stage_enum "
        "USING stage::text::pipeline_stage_enum"
    )
    op.execute("DROP TYPE pipeline_stage_enum_old")
