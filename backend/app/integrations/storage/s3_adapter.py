"""`StoragePort` adapter over any S3-compatible provider (PLAN §16.1, ADR-009).

Path-style addressing (`addressing_style="path"`) is required for MinIO —
virtual-hosted-style (the boto3 default) needs DNS wildcarding MinIO doesn't
provide locally. Real S3/R2 accept path-style too, so one client config
works across every environment (§17.3, §20.1).
"""

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import Settings
from app.core.errors import IntegrationError


class S3StorageAdapter:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.storage_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            region_name=settings.storage_region,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            use_ssl=settings.storage_use_ssl,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    def put_object(self, key: str, data: bytes, *, content_type: str) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
        except ClientError as exc:
            raise IntegrationError(f"Storage write failed for {key}") from exc

    def get_object(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()  # type: ignore[no-any-return]
        except ClientError as exc:
            raise IntegrationError(f"Storage read failed for {key}") from exc

    def delete_object(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            raise IntegrationError(f"Storage delete failed for {key}") from exc

    def presigned_upload_url(self, key: str, *, content_type: str, expires_in_seconds: int) -> str:
        try:
            return str(
                self._client.generate_presigned_url(
                    "put_object",
                    Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
                    ExpiresIn=expires_in_seconds,
                )
            )
        except ClientError as exc:
            raise IntegrationError(f"Presigned upload URL failed for {key}") from exc

    def presigned_download_url(self, key: str, *, expires_in_seconds: int) -> str:
        try:
            return str(
                self._client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self._bucket, "Key": key},
                    ExpiresIn=expires_in_seconds,
                )
            )
        except ClientError as exc:
            raise IntegrationError(f"Presigned download URL failed for {key}") from exc
