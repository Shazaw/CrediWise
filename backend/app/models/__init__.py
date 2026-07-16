"""Import every model module so `Base.metadata` is fully populated before
Alembic autogenerate or `Base.metadata.create_all()` (integration tests) run.
"""

from app.models.audit_log import AuditLog
from app.models.model_version import ModelVersion
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserIdentity, UserProfile

__all__ = [
    "AuditLog",
    "ModelVersion",
    "RefreshToken",
    "User",
    "UserIdentity",
    "UserProfile",
]
