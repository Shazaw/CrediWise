"""auth: users, user_profiles, user_identities, refresh_tokens, audit_logs, model_versions

Sprint 1 identity and governance schema (PLAN §11.3, §18.1, §19.2, T1.1/T1.6/T1.7).

`refresh_tokens` is not in PLAN §11.3's original table catalogue but is
required by the already-documented decision in §18.1 ("refresh tokens are
stored server-side (hashed) so they can be revoked"); PLAN.md §11.3 is
updated in the same PR per §24.11.

`updated_at` is trigger-updated per §11.1 rather than relying only on the
ORM's `onupdate`, so direct SQL updates stay consistent too.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# `create_type=False`: these ENUM objects are used only to drive explicit
# `.create()`/`.drop()` calls below. Without this, SQLAlchemy would try to
# (re)issue CREATE/DROP TYPE itself on every table that references the type,
# which fails the second time the same type is used across multiple tables.
_role_enum = postgresql.ENUM(
    "USER", "LENDER", "REVIEWER", "ADMIN", name="role_enum", create_type=False
)
_identity_status_enum = postgresql.ENUM(
    "UNVERIFIED", "PENDING", "VERIFIED", "REJECTED", name="identity_status_enum", create_type=False
)
_employment_enum = postgresql.ENUM(
    "EMPLOYED",
    "SELF_EMPLOYED",
    "GIG_WORKER",
    "BUSINESS_OWNER",
    "UNEMPLOYED",
    "OTHER",
    name="employment_enum",
    create_type=False,
)
_doc_type_enum = postgresql.ENUM(
    "KTP", "PASSPORT", "OTHER", name="doc_type_enum", create_type=False
)
_verify_status_enum = postgresql.ENUM(
    "PENDING", "VERIFIED", "REJECTED", name="verify_status_enum", create_type=False
)
_actor_enum = postgresql.ENUM(
    "USER", "LENDER", "SYSTEM", "ADMIN", name="actor_enum", create_type=False
)
_model_status_enum = postgresql.ENUM(
    "DRAFT", "ACTIVE", "RETIRED", name="model_status_enum", create_type=False
)

_ENUMS = [
    _role_enum,
    _identity_status_enum,
    _employment_enum,
    _doc_type_enum,
    _verify_status_enum,
    _actor_enum,
    _model_status_enum,
]

_TRIGGERED_TABLES = [
    "users",
    "user_profiles",
    "user_identities",
    "refresh_tokens",
    "model_versions",
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
    op.execute('CREATE EXTENSION IF NOT EXISTS "citext"')
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    bind = op.get_bind()
    for enum_type in _ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        *_timestamp_columns(),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", _role_enum, nullable=False, server_default="USER"),
        sa.Column(
            "identity_status", _identity_status_enum, nullable=False, server_default="UNVERIFIED"
        ),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_users_email_active",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "user_profiles",
        *_timestamp_columns(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("employment_type", _employment_enum, nullable=True),
        sa.Column("business_type", sa.Text(), nullable=True),
        sa.Column("locale", sa.Text(), nullable=False, server_default="id-ID"),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True)

    op.create_table(
        "user_identities",
        *_timestamp_columns(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("document_type", _doc_type_enum, nullable=True),
        sa.Column("document_number_hash", sa.Text(), nullable=True),
        sa.Column("verified_name", sa.Text(), nullable=True),
        sa.Column(
            "verification_status", _verify_status_enum, nullable=False, server_default="PENDING"
        ),
        sa.Column("verification_provider", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_user_identities_user_id", "user_identities", ["user_id"])

    op.create_table(
        "refresh_tokens",
        *_timestamp_columns(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.CHAR(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "replaced_by_token_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("refresh_tokens.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index(
        "ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True
    )

    op.create_table(
        "audit_logs",
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
        sa.Column("actor_type", _actor_enum, nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_actor_created", "audit_logs", ["actor_id", "created_at"])
    # Append-only by convention: application code never issues UPDATE/DELETE
    # against this table. DB-level role grants enforcing that are production
    # hardening (PLAN Sprint 10, §11.3).

    op.create_table(
        "model_versions",
        *_timestamp_columns(),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("status", _model_status_enum, nullable=False, server_default="DRAFT"),
        sa.Column("config_hash", sa.CHAR(64), nullable=False),
        sa.Column("training_data_reference", sa.Text(), nullable=True),
        sa.Column("validation_metrics_json", postgresql.JSONB(), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_model_versions_one_active_per_name",
        "model_versions",
        ["model_name"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND deleted_at IS NULL"),
    )

    for table_name in _TRIGGERED_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_updated_at BEFORE UPDATE ON {table_name} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    op.drop_table("model_versions")
    op.drop_table("audit_logs")
    op.drop_table("refresh_tokens")
    op.drop_table("user_identities")
    op.drop_table("user_profiles")
    op.drop_table("users")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at() CASCADE")

    bind = op.get_bind()
    for enum_type in reversed(_ENUMS):
        enum_type.drop(bind, checkfirst=True)

    op.execute('DROP EXTENSION IF EXISTS "citext"')
