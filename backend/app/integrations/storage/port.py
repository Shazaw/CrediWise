"""`StoragePort` — the object-storage integration interface (PLAN §16.1, ADR-009).

Behind this interface, MVP uses MinIO locally and any S3-compatible provider
(Cloudflare R2 / AWS S3) in staging/production (§17.3) — only the endpoint
and credentials differ. Services and the document pipeline depend on this
protocol, never on `boto3` directly (PLAN §10.1 integrations layer).
"""

from typing import Protocol


class StoragePort(Protocol):
    def put_object(self, key: str, data: bytes, *, content_type: str) -> None:
        """Write `data` to `key`, server-side-encrypted at rest (PLAN §17.3)."""
        ...

    def get_object(self, key: str) -> bytes:
        """Read the full object at `key`. Raises `IntegrationError` if missing."""
        ...

    def delete_object(self, key: str) -> None:
        """Hard-delete `key` (used only by the retention/erasure job, §11.5)."""
        ...

    def presigned_upload_url(self, key: str, *, content_type: str, expires_in_seconds: int) -> str:
        """A short-lived URL a client may `PUT` directly to (§17.3)."""
        ...

    def presigned_download_url(self, key: str, *, expires_in_seconds: int) -> str:
        """A short-lived URL a client may `GET` directly from (§17.3)."""
        ...


def raw_document_key(user_id: str, document_id: str) -> str:
    """Bucket layout: `raw/{user_id}/{document_id}` (PLAN §17.3) — no
    user-supplied filename ever enters the storage key (FR-3 AC5: storage
    keys are server-generated, not derived from client input)."""
    return f"raw/{user_id}/{document_id}"
