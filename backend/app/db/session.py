"""SQLAlchemy engine and session factory (sync — ADR-004).

One uniform session pattern is used across the FastAPI threadpool and Celery
workers. ``get_db`` is the FastAPI dependency; Celery tasks use
``SessionLocal()`` directly with an explicit try/commit/rollback/close.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
