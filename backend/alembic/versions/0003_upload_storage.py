"""upload storage: financial_accounts, source_documents

Sprint 2 upload/file-security/storage schema (PLAN §11.3, §25 Sprint 2,
T2.1). `ownership_enum`/`conn_status_enum` member sets and `doc_status_enum`'s
`VALIDATION_FAILED`/`DUPLICATE_REUSED` additions are Sprint 2 gap-fills
(PLAN §24.11) — see `app/models/enums.py` and PLAN.md §11.3/Appendix A for
the documented rationale.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_account_type_enum = postgresql.ENUM(
    "BANK", "EWALLET", "QRIS", "MARKETPLACE", name="account_type_enum", create_type=False
)
_ownership_enum = postgresql.ENUM(
    "DECLARED", "VERIFIED", name="ownership_enum", create_type=False
)
_conn_type_enum = postgresql.ENUM("UPLOAD", "API", name="conn_type_enum", create_type=False)
_conn_status_enum = postgresql.ENUM(
    "ACTIVE", "INACTIVE", "ERROR", name="conn_status_enum", create_type=False
)
_source_type_enum = postgresql.ENUM(
    "BANK_API",
    "SIGNED_STATEMENT",
    "ORIGINAL_PDF",
    "EXPORTED_CSV",
    "SCREENSHOT",
    "PHOTO",
    name="source_type_enum",
    create_type=False,
)
_doc_status_enum = postgresql.ENUM(
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
    name="doc_status_enum",
    create_type=False,
)

_ENUMS = [
    _account_type_enum,
    _ownership_enum,
    _conn_type_enum,
    _conn_status_enum,
    _source_type_enum,
    _doc_status_enum,
]

_TRIGGERED_TABLES = ["financial_accounts", "source_documents"]


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
        "financial_accounts",
        *_timestamp_columns(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("account_type", _account_type_enum, nullable=False),
        sa.Column("provider_name", sa.Text(), nullable=True),
        sa.Column("masked_account_number", sa.Text(), nullable=True),
        sa.Column("ownership_status", _ownership_enum, nullable=False, server_default="DECLARED"),
        sa.Column("connection_type", _conn_type_enum, nullable=False),
        sa.Column("connection_status", _conn_status_enum, nullable=False, server_default="ACTIVE"),
    )
    op.create_index(
        "ix_financial_accounts_user_type", "financial_accounts", ["user_id", "account_type"]
    )

    op.create_table(
        "source_documents",
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
            nullable=True,
        ),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("file_hash", sa.CHAR(64), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("source_type", _source_type_enum, nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("statement_start_date", sa.Date(), nullable=True),
        sa.Column("statement_end_date", sa.Date(), nullable=True),
        sa.Column("status", _doc_status_enum, nullable=False, server_default="UPLOADED"),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_source_documents_user_hash",
        "source_documents",
        ["user_id", "file_hash"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_source_documents_user_status", "source_documents", ["user_id", "status"]
    )

    for table_name in _TRIGGERED_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_updated_at BEFORE UPDATE ON {table_name} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    op.drop_table("source_documents")
    op.drop_table("financial_accounts")

    bind = op.get_bind()
    for enum_type in reversed(_ENUMS):
        enum_type.drop(bind, checkfirst=True)
