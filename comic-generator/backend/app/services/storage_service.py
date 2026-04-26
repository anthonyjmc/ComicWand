"""Cloudflare R2 storage service abstraction."""

from __future__ import annotations

import time
from urllib.parse import urlparse

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from loguru import logger

from app.core.config import get_settings

MAX_RETRIES = 3


class StorageService:
    """Cloudflare R2 wrapper around boto3."""

    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.cloudflare_r2_bucket
        self.endpoint = settings.cloudflare_r2_endpoint.rstrip("/")
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.cloudflare_r2_endpoint,
            aws_access_key_id=settings.cloudflare_r2_access_key,
            aws_secret_access_key=settings.cloudflare_r2_secret_key,
            region_name="auto",
        )
        parsed_endpoint = urlparse(settings.cloudflare_r2_endpoint)
        self.public_base_url = f"{parsed_endpoint.scheme}://{self.bucket}.{parsed_endpoint.netloc}"

    def upload_file(self, file_bytes: bytes, path: str, content_type: str) -> str:
        """Upload file bytes and return public URL."""
        operation_started_at = time.perf_counter()
        logger.bind(user_id="system", action="storage_upload", duration_ms=0).info(
            "Storage upload started path={path}",
            path=path,
        )
        self._retry_operation(
            action="storage_upload",
            operation=lambda: self.client.put_object(
                Bucket=self.bucket,
                Key=path,
                Body=file_bytes,
                ContentType=content_type,
            ),
        )
        duration_ms = int((time.perf_counter() - operation_started_at) * 1000)
        logger.bind(user_id="system", action="storage_upload", duration_ms=duration_ms).info(
            "Storage upload finished path={path}",
            path=path,
        )
        return f"{self.public_base_url}/{path}"

    def get_signed_url(self, path: str, expires_in: int = 604800) -> str:
        """Create signed URL for a stored object."""
        operation_started_at = time.perf_counter()
        logger.bind(user_id="system", action="storage_sign_url", duration_ms=0).info(
            "Signed URL generation started path={path}",
            path=path,
        )
        signed_url = self._retry_operation(
            action="storage_sign_url",
            operation=lambda: self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": path},
                ExpiresIn=expires_in,
            ),
        )
        duration_ms = int((time.perf_counter() - operation_started_at) * 1000)
        logger.bind(user_id="system", action="storage_sign_url", duration_ms=duration_ms).info(
            "Signed URL generation finished path={path}",
            path=path,
        )
        return str(signed_url)

    def delete_file(self, path: str) -> bool:
        """Delete file from R2 bucket."""
        operation_started_at = time.perf_counter()
        logger.bind(user_id="system", action="storage_delete", duration_ms=0).info(
            "Storage delete started path={path}",
            path=path,
        )
        self._retry_operation(
            action="storage_delete",
            operation=lambda: self.client.delete_object(Bucket=self.bucket, Key=path),
        )
        duration_ms = int((time.perf_counter() - operation_started_at) * 1000)
        logger.bind(user_id="system", action="storage_delete", duration_ms=duration_ms).info(
            "Storage delete finished path={path}",
            path=path,
        )
        return True

    def _retry_operation(self, *, action: str, operation: callable):
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            attempt_started_at = time.perf_counter()
            try:
                return operation()
            except (ClientError, BotoCoreError, TimeoutError, ValueError) as exc:
                last_error = exc
                duration_ms = int((time.perf_counter() - attempt_started_at) * 1000)
                logger.bind(user_id="system", action=action, duration_ms=duration_ms).warning(
                    "Storage operation failed attempt={attempt} error_type={error_type}",
                    attempt=attempt,
                    error_type=type(exc).__name__,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** (attempt - 1))
            except Exception as exc:
                last_error = exc
                duration_ms = int((time.perf_counter() - attempt_started_at) * 1000)
                logger.bind(user_id="system", action=action, duration_ms=duration_ms).error(
                    "Unexpected storage error attempt={attempt} error_type={error_type}",
                    attempt=attempt,
                    error_type=type(exc).__name__,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** (attempt - 1))

        if last_error is None:
            raise RuntimeError("Storage operation failed without a specific error")
        raise RuntimeError(f"Storage operation failed after {MAX_RETRIES} attempts") from last_error
