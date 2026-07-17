"""Idempotently activates the exact current immutable model configuration."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.config.model_config import MODEL_NAME, MODEL_VERSION, config_hash
from app.models.enums import ModelStatusEnum
from app.models.model_version import ModelVersion


def run(session: Session) -> None:
    now = datetime.now(UTC)
    current_hash = config_hash()
    rows = list(
        session.execute(
            select(ModelVersion).where(
                ModelVersion.model_name == MODEL_NAME,
                ModelVersion.deleted_at.is_(None),
            )
        ).scalars()
    )
    exact = next(
        (row for row in rows if row.version == MODEL_VERSION and row.config_hash == current_hash),
        None,
    )
    for row in rows:
        if row.status == ModelStatusEnum.ACTIVE and row is not exact:
            row.status = ModelStatusEnum.RETIRED
            row.retired_at = now
    # The partial unique index permits one ACTIVE row per model name. Flush
    # retirement before inserting/activating the exact current configuration.
    session.flush()
    if exact is None:
        exact = ModelVersion(
            model_name=MODEL_NAME,
            version=MODEL_VERSION,
            status=ModelStatusEnum.DRAFT,
            config_hash=current_hash,
            released_at=now,
        )
        session.add(exact)
    exact.status = ModelStatusEnum.ACTIVE
    exact.retired_at = None
