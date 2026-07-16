"""Seeds the initial ACTIVE `model_versions` row (PLAN §19.2, T1.7).

Idempotent: re-running does nothing once an ACTIVE row for `MODEL_NAME`
exists (PLAN §11.4 — seed data must be safe to re-run).
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.config.model_config import MODEL_NAME, MODEL_VERSION, config_hash
from app.models.enums import ModelStatusEnum
from app.models.model_version import ModelVersion


def run(session: Session) -> None:
    exists = session.execute(
        select(ModelVersion).where(
            ModelVersion.model_name == MODEL_NAME,
            ModelVersion.status == ModelStatusEnum.ACTIVE,
            ModelVersion.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if exists is not None:
        return
    session.add(
        ModelVersion(
            model_name=MODEL_NAME,
            version=MODEL_VERSION,
            status=ModelStatusEnum.ACTIVE,
            config_hash=config_hash(),
            released_at=datetime.now(UTC),
        )
    )
