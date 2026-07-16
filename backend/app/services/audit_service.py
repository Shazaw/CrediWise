"""Append-only audit trail writer (PLAN §10.5, §11.3, FR-15).

Called directly by other services within the same DB transaction as the
state change it records — the simplest correct implementation of PLAN
§10.5's "single audit subscriber" for the services that exist so far.
`audit_logs` rows are never updated or deleted by application code.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_correlation_id
from app.models.audit_log import AuditLog
from app.models.enums import ActorTypeEnum


def record(
    db: Session,
    *,
    actor_type: ActorTypeEnum,
    actor_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata or {},
        correlation_id=_parse_correlation_id(),
    )
    db.add(entry)
    db.flush()
    return entry


def _parse_correlation_id() -> uuid.UUID | None:
    """The correlation-id middleware accepts a client-supplied, non-UUID
    header value (PLAN §20.3 only requires it be echoed and logged); the
    `audit_logs.correlation_id` column is typed UUID (PLAN §11.3), so a
    malformed value is stored as NULL rather than failing the audit write.
    """
    correlation_id = get_correlation_id()
    if correlation_id is None:
        return None
    try:
        return uuid.UUID(correlation_id)
    except ValueError:
        return None
