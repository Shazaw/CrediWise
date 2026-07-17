"""Add versioned shadow repayment-model evidence.

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_prediction_status = postgresql.ENUM(
    "COMPLETE",
    "INELIGIBLE",
    "UNAVAILABLE",
    name="repayment_prediction_status_enum",
    create_type=False,
)
_model_mode = postgresql.ENUM(
    "SHADOW_RESEARCH", name="repayment_model_mode_enum", create_type=False
)
_band_enum = postgresql.ENUM("HIGH", "MEDIUM", "LOW", name="band_enum", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    _prediction_status.create(bind, checkfirst=True)
    _model_mode.create(bind, checkfirst=True)

    for name, column_type in (
        ("artifact_uri", sa.Text()),
        ("artifact_sha256", sa.CHAR(64)),
        ("artifact_format", sa.Text()),
        ("feature_schema_version", sa.Text()),
        ("feature_schema_hash", sa.CHAR(64)),
        ("target_version", sa.Text()),
        ("runtime_contract_version", sa.Text()),
        ("model_card_uri", sa.Text()),
    ):
        op.add_column("model_versions", sa.Column(name, column_type, nullable=True))

    op.create_table(
        "repayment_model_predictions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("mode", _model_mode, nullable=False),
        sa.Column("status", _prediction_status, nullable=False),
        sa.Column("feature_schema_version", sa.Text(), nullable=False),
        sa.Column("feature_hash", sa.CHAR(64), nullable=True),
        sa.Column("feature_vector_json", postgresql.JSONB(), nullable=True),
        sa.Column("artifact_sha256", sa.CHAR(64), nullable=False),
        sa.Column("raw_probability", sa.Numeric(8, 6), nullable=True),
        sa.Column("calibrated_probability", sa.Numeric(8, 6), nullable=True),
        sa.Column("model_confidence", _band_enum, nullable=True),
        sa.Column(
            "reason_codes_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "out_of_domain_features_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("failure_code", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "raw_probability IS NULL OR (raw_probability >= 0 AND raw_probability <= 1)",
            name="ck_repayment_prediction_raw_probability",
        ),
        sa.CheckConstraint(
            "calibrated_probability IS NULL OR "
            "(calibrated_probability >= 0 AND calibrated_probability <= 1)",
            name="ck_repayment_prediction_calibrated_probability",
        ),
        sa.UniqueConstraint(
            "assessment_id",
            "model_version_id",
            "mode",
            name="uq_repayment_prediction_assessment_model_mode",
        ),
    )
    op.create_index(
        "ix_repayment_model_predictions_assessment",
        "repayment_model_predictions",
        ["assessment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_repayment_model_predictions_assessment",
        table_name="repayment_model_predictions",
    )
    op.drop_table("repayment_model_predictions")
    for name in (
        "model_card_uri",
        "runtime_contract_version",
        "target_version",
        "feature_schema_hash",
        "feature_schema_version",
        "artifact_format",
        "artifact_sha256",
        "artifact_uri",
    ):
        op.drop_column("model_versions", name)
    bind = op.get_bind()
    _model_mode.drop(bind, checkfirst=True)
    _prediction_status.drop(bind, checkfirst=True)
