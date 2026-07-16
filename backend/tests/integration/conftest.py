"""Real-Postgres DB fixtures for integration tests (PLAN §21.1).

Requires a reachable Postgres at `DB_HOST`/`DB_PORT` (see `tests/conftest.py`
for local defaults; CI provisions a `postgres:16` service — see
`.github/workflows/backend-ci.yml`). Schema is created via
`Base.metadata.create_all` rather than Alembic — migration correctness is
verified separately by the `alembic upgrade/downgrade/upgrade` CI step
(PLAN §20.2), so these fixtures don't pay that cost per test session.

`authed_client` is a distinct fixture name from the root `client` fixture
(`tests/conftest.py`) so tests that don't need a real DB — like the existing
`tests/integration/api/test_health.py` — are unaffected.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 - populates Base.metadata
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.integrations.storage import set_storage_port
from app.integrations.storage.s3_adapter import S3StorageAdapter
from app.pipeline import dispatch


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    settings = get_settings()
    engine = create_engine(settings.sqlalchemy_database_uri, future=True)
    with engine.connect() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "citext"'))
        conn.commit()
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """Wraps each test in a transaction that's rolled back after — tests
    never see each other's data even though they share `db_engine`."""
    connection = db_engine.connect()
    transaction = connection.begin()
    test_session_local = sessionmaker(bind=connection, autoflush=False, future=True)
    session = test_session_local()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def authed_client(db_session: Session) -> Iterator[TestClient]:
    from app.main import app

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _inline_document_processing(db_session: Session) -> Iterator[None]:
    """Runs `process_document`'s logic inline against the test's own
    `db_session` instead of a real Celery broker + a second, separately
    connected `SessionLocal` (see `app/pipeline/dispatch.py`)."""
    from app.pipeline.document_tasks import run_security_and_enqueue_extraction

    dispatch.set_dispatch_override(
        lambda document_id: run_security_and_enqueue_extraction(db_session, document_id)
    )
    yield
    dispatch.set_dispatch_override(None)


@pytest.fixture(autouse=True)
def _mock_storage() -> Iterator[None]:
    """`moto` intercepts AWS-shaped endpoints (see `tests/unit/test_storage_adapter.py`
    for why the endpoint here differs from the app's real MinIO `STORAGE_ENDPOINT_URL`)."""
    settings = Settings(
        storage_endpoint_url="https://s3.amazonaws.com",
        storage_region="us-east-1",
        storage_bucket="crediwise-test-bucket",
        storage_access_key="testing",
        storage_secret_key="testing",
    )
    with mock_aws():
        set_storage_port(S3StorageAdapter(settings))
        yield
    set_storage_port(None)
