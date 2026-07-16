"""Process-wide `StoragePort` singleton (PLAN §16.1).

Mirrors `app.core.rate_limit`'s `get_redis_client`/`set_redis_client` seam:
`set_storage_port` lets tests inject a fake/mocked adapter instead of
constructing a real `S3StorageAdapter`.
"""

from app.core.config import get_settings
from app.integrations.storage.port import StoragePort, raw_document_key
from app.integrations.storage.s3_adapter import S3StorageAdapter

__all__ = ["StoragePort", "get_storage_port", "raw_document_key", "set_storage_port"]

_storage_port: StoragePort | None = None


def get_storage_port() -> StoragePort:
    global _storage_port
    if _storage_port is None:
        _storage_port = S3StorageAdapter(get_settings())
    return _storage_port


def set_storage_port(port: StoragePort | None) -> None:
    """Test hook — inject a fake/mocked `StoragePort` instead of a real one."""
    global _storage_port
    _storage_port = port
