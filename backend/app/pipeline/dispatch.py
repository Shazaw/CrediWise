"""Overridable seam for enqueueing pipeline work (PLAN §17.1).

Mirrors `app.core.rate_limit`'s `get_redis_client`/`set_redis_client` pattern:
production dispatches through Celery; gate tests inject a synchronous
override (see `tests/integration/conftest.py`) so `run_security_and_enqueue_extraction`
runs against the same DB session/transaction the test already has, instead of
a real broker + a second, separately-connected session (PLAN §21.1 — local,
reproducible, no broker dependency in the general test suite).
"""

import uuid
from collections.abc import Callable

_dispatch_override: Callable[[uuid.UUID], None] | None = None


def set_dispatch_override(dispatcher: Callable[[uuid.UUID], None] | None) -> None:
    """Test hook — replace the real Celery dispatch with a direct call."""
    global _dispatch_override
    _dispatch_override = dispatcher


def dispatch_document_processing(document_id: uuid.UUID) -> None:
    if _dispatch_override is not None:
        _dispatch_override(document_id)
        return
    from app.pipeline.document_tasks import process_document

    process_document.delay(str(document_id))
