"""extraction & trust layer: document_processing_runs, transactions,
document_verification_results, pipeline_stage_runs, corrections

Sprint 3 OCR/extraction/Trust-Layer schema (PLAN §11.3, §25 Sprint 3, T3.2).
`processing_status_enum`, `pipeline_stage_enum`, `stage_status_enum`, and
`dir_enum` member sets are Sprint 3 gap-fills (PLAN §24.11) — see
`app/models/enums.py` and PLAN.md §11.3/Appendix A. `corrections` is brought
forward from PLAN §7.13's POST-MVP tag because FR-14/T3.6's MVP review flow
needs it now (see `app/models/correction.py`).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_processing_status_enum = postgresql.ENUM(
    "RUNNING", "COMPLETE", "FAILED", name="processing_status_enum", create_type=False
)
_pipeline_stage_enum = postgresql.ENUM(
    "EXTRACTION", "VERIFICATION", name="pipeline_stage_enum", create_type=False
)
_stage_status_enum = postgresql.ENUM(
    "RUNNING", "SUCCEEDED", "FAILED", name="stage_status_enum", create_type=False
)
_dir_enum = postgresql.ENUM("CREDIT", "DEBIT", name="dir_enum", create_type=False)
_category_enum = postgresql.ENUM(
    "INCOME",
    "ESSENTIAL_EXPENSE",
    "FINANCIAL_OBLIGATION",
    "DISCRETIONARY",
    "SAVINGS_TRANSFER",
    "INTERNAL_TRANSFER",
    "UNKNOWN",
    name="category_enum",
    create_type=False,
)
_transaction_context_enum = postgresql.ENUM(
    "PERSONAL", "BUSINESS", "MIXED", "UNKNOWN", name="transaction_context_enum", create_type=False
)
_band_enum = postgresql.ENUM("HIGH", "MEDIUM", "LOW", name="band_enum", create_type=False)

_ENUMS = [
    _processing_status_enum,
    _pipeline_stage_enum,
    _stage_status_enum,
    _dir_enum,
    _category_enum,
    _transaction_context_enum,
    _band_enum,
]

_TRIGGERED_TABLES = [
    "document_processing_runs",
    "transactions",
    "document_verification_results",
    "pipeline_stage_runs",
    "corrections",
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
    bind = op.get_bind()
    for enum_type in _ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "document_processing_runs",
        *_timestamp_columns(),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("parser_name", sa.Text(), nullable=False),
        sa.Column("parser_version", sa.Text(), nullable=False),
        sa.Column("format_name", sa.Text(), nullable=False),
        sa.Column("format_detection_confidence", sa.Numeric(6, 4), nullable=False),
        sa.Column(
            "status", _processing_status_enum, nullable=False, server_default="RUNNING"
        ),
        sa.Column("input_hash", sa.CHAR(64), nullable=False),
        sa.Column("output_hash", sa.CHAR(64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "supersedes_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_processing_runs.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_document_processing_runs_source_document",
        "document_processing_runs",
        ["source_document_id"],
    )

    op.create_table(
        "transactions",
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
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_documents.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "processing_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_processing_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("transaction_time", sa.Time(), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("direction", _dir_enum, nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default="IDR"),
        sa.Column("balance_after", sa.BigInteger(), nullable=True),
        sa.Column("raw_description", sa.Text(), nullable=False),
        sa.Column("normalized_merchant", sa.Text(), nullable=True),
        sa.Column("category", _category_enum, nullable=False, server_default="UNKNOWN"),
        sa.Column("subcategory", sa.Text(), nullable=True),
        sa.Column(
            "transaction_context",
            _transaction_context_enum,
            nullable=False,
            server_default="UNKNOWN",
        ),
        sa.Column("counterparty", sa.Text(), nullable=True),
        sa.Column("is_internal_transfer", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("category_confidence", sa.Numeric(6, 4), nullable=True),
        sa.Column("extraction_confidence", sa.Numeric(6, 4), nullable=False),
        sa.Column("row_hash", sa.CHAR(64), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
    )
    op.create_index("ix_transactions_user_date", "transactions", ["user_id", "transaction_date"])
    op.create_index(
        "ix_transactions_account_date", "transactions", ["financial_account_id", "transaction_date"]
    )
    op.create_index("ix_transactions_processing_run", "transactions", ["processing_run_id"])
    op.create_index(
        "ix_transactions_run_row_hash",
        "transactions",
        ["processing_run_id", "row_hash"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "document_verification_results",
        *_timestamp_columns(),
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
            "verification_model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "supersedes_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_verification_results.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("metadata_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("consistency_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("visual_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("ocr_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("completeness_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("ownership_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("provenance_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("data_confidence_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("confidence_band", _band_enum, nullable=False),
        sa.Column(
            "flags_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_document_verification_results_source_document",
        "document_verification_results",
        ["source_document_id"],
    )

    op.create_table(
        "pipeline_stage_runs",
        *_timestamp_columns(),
        sa.Column(
            "source_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_documents.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("stage", _pipeline_stage_enum, nullable=False),
        sa.Column("status", _stage_status_enum, nullable=False, server_default="RUNNING"),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("input_hash", sa.CHAR(64), nullable=True),
        sa.Column("output_hash", sa.CHAR(64), nullable=True),
        sa.Column("worker_version", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("sanitized_error_message", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_pipeline_stage_runs_document_stage",
        "pipeline_stage_runs",
        ["source_document_id", "stage"],
    )

    op.create_table(
        "corrections",
        *_timestamp_columns(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("correction_type", sa.Text(), nullable=False),
        sa.Column(
            "payload_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
    )
    op.create_index("ix_corrections_user", "corrections", ["user_id"])
    op.create_index("ix_corrections_transaction", "corrections", ["transaction_id"])

    for table_name in _TRIGGERED_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_updated_at BEFORE UPDATE ON {table_name} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    op.drop_table("corrections")
    op.drop_table("pipeline_stage_runs")
    op.drop_table("document_verification_results")
    op.drop_table("transactions")
    op.drop_table("document_processing_runs")

    bind = op.get_bind()
    for enum_type in reversed(_ENUMS):
        enum_type.drop(bind, checkfirst=True)
