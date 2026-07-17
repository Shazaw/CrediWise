from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.seeds import lenders, model_versions
from app.engines.config import model_config
from app.models.enums import ModelStatusEnum, RegStatusEnum
from app.models.model_version import ModelVersion


def test_model_seed_retires_prior_active_version_without_mutating_it(db_session: Session) -> None:
    current = db_session.execute(
        select(ModelVersion).where(
            ModelVersion.model_name == model_config.MODEL_NAME,
            ModelVersion.status == ModelStatusEnum.ACTIVE,
        )
    ).scalar_one()
    current.status = ModelStatusEnum.RETIRED
    db_session.flush()
    prior = ModelVersion(
        model_name=model_config.MODEL_NAME,
        version="v1",
        status=ModelStatusEnum.ACTIVE,
        config_hash="1" * 64,
        released_at=datetime.now(UTC),
    )
    db_session.add(prior)
    db_session.flush()

    model_versions.run(db_session)
    db_session.flush()

    assert prior.status is ModelStatusEnum.RETIRED
    assert prior.config_hash == "1" * 64
    current = db_session.execute(
        select(ModelVersion).where(
            ModelVersion.model_name == model_config.MODEL_NAME,
            ModelVersion.version == model_config.MODEL_VERSION,
            ModelVersion.config_hash == model_config.config_hash(),
        )
    ).scalar_one()
    assert current.status is ModelStatusEnum.ACTIVE


def test_model_seed_does_not_activate_same_version_with_wrong_hash(db_session: Session) -> None:
    current = db_session.execute(
        select(ModelVersion).where(
            ModelVersion.model_name == model_config.MODEL_NAME,
            ModelVersion.status == ModelStatusEnum.ACTIVE,
        )
    ).scalar_one()
    current.status = ModelStatusEnum.RETIRED
    db_session.flush()
    mismatch = ModelVersion(
        model_name=model_config.MODEL_NAME,
        version=model_config.MODEL_VERSION,
        status=ModelStatusEnum.ACTIVE,
        config_hash="f" * 64,
        released_at=datetime.now(UTC),
    )
    db_session.add(mismatch)
    db_session.flush()

    model_versions.run(db_session)
    db_session.flush()

    assert mismatch.status is ModelStatusEnum.RETIRED
    active = list(
        db_session.execute(
            select(ModelVersion).where(
                ModelVersion.model_name == model_config.MODEL_NAME,
                ModelVersion.status == ModelStatusEnum.ACTIVE,
            )
        ).scalars()
    )
    assert len(active) == 1
    assert active[0].config_hash == model_config.config_hash()


def test_all_seeded_mvp_lenders_are_simulated_regulated(db_session: Session) -> None:
    lenders.run(db_session)
    db_session.flush()

    assert all(
        entry["regulatory_status"] is RegStatusEnum.SIMULATED_REGULATED_PROVIDER
        for entry in lenders.SEEDED_LENDERS
    )
