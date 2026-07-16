"""`S3StorageAdapter` tests against a mocked S3 (PLAN §16.1, ADR-009).

`moto` provides a deterministic, in-process fake S3 — no real MinIO/network
needed, keeping this a gate test (CLAUDE.md §7.1: local, reproducible,
isolated, free of public network dependencies). `moto` intercepts calls by
matching AWS-shaped endpoints, so the settings used here point at a plain
AWS endpoint rather than the real app's MinIO `STORAGE_ENDPOINT_URL` — the
adapter code under test is unchanged; only the endpoint differs, exactly as
it would between local MinIO and staging/production S3 (PLAN §17.3).
"""

from collections.abc import Iterator

import pytest
from moto import mock_aws

from app.core.config import Settings
from app.core.errors import IntegrationError
from app.integrations.storage.port import raw_document_key
from app.integrations.storage.s3_adapter import S3StorageAdapter


@pytest.fixture
def adapter() -> Iterator[S3StorageAdapter]:
    settings = Settings(
        storage_endpoint_url="https://s3.amazonaws.com",
        storage_region="us-east-1",
        storage_bucket="crediwise-test-bucket",
        storage_access_key="testing",
        storage_secret_key="testing",
    )
    with mock_aws():
        yield S3StorageAdapter(settings)


def test_put_then_get_round_trips_bytes(adapter: S3StorageAdapter) -> None:
    key = raw_document_key("user-1", "doc-1")
    adapter.put_object(key, b"%PDF-1.4 fixture bytes", content_type="application/pdf")

    assert adapter.get_object(key) == b"%PDF-1.4 fixture bytes"


def test_delete_removes_object(adapter: S3StorageAdapter) -> None:
    key = raw_document_key("user-1", "doc-2")
    adapter.put_object(key, b"data", content_type="text/csv")

    adapter.delete_object(key)

    with pytest.raises(IntegrationError):
        adapter.get_object(key)


def test_get_missing_object_raises_integration_error(adapter: S3StorageAdapter) -> None:
    with pytest.raises(IntegrationError):
        adapter.get_object(raw_document_key("user-1", "does-not-exist"))


def test_presigned_upload_url_is_a_put_able_url(adapter: S3StorageAdapter) -> None:
    key = raw_document_key("user-1", "doc-3")

    url = adapter.presigned_upload_url(key, content_type="application/pdf", expires_in_seconds=60)

    assert url.startswith("http")
    assert key in url


def test_presigned_download_url_is_a_get_able_url(adapter: S3StorageAdapter) -> None:
    key = raw_document_key("user-1", "doc-4")
    adapter.put_object(key, b"data", content_type="text/csv")

    url = adapter.presigned_download_url(key, expires_in_seconds=60)

    assert url.startswith("http")
    assert key in url
