"""Celery application instance (PLAN §17.1).

Three queues split by workload: ``documents`` (OCR/verify, CPU/IO heavy),
``analysis`` (engines + optional explanation adapter), and ``maintenance``
(retention/erasure, audit compaction, Celery beat schedule). Task modules for
each queue land starting Sprint 2; this scaffold only wires the app so the
``worker`` container in docker-compose can boot in Sprint 0.
"""

from celery import Celery
from kombu import Queue

from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging()

celery_app = Celery(
    "crediwise",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_default_queue="documents",
    task_queues=(
        Queue("documents"),
        Queue("analysis"),
        Queue("maintenance"),
    ),
)


@celery_app.task(name="app.pipeline.ping")
def ping() -> str:
    """Smoke-test task confirming a worker is consuming the queue."""
    return "pong"
