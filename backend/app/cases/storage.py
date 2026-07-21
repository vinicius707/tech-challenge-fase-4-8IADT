"""Object store de Artefatos (MinIO em runtime; fake em testes)."""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from typing import Protocol

import urllib3
from minio import Minio


class ArtifactStorageError(Exception):
    """Falha ao gravar/ler Artefato no object store."""


class ArtifactBlobStore(Protocol):
    def put(
        self,
        *,
        bucket: str,
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> None: ...

    def get(self, bucket: str, object_key: str) -> bytes | None: ...


@dataclass
class InMemoryArtifactBlobStore:
    _objects: dict[tuple[str, str], bytes] = field(default_factory=dict)

    def put(
        self,
        *,
        bucket: str,
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        _ = content_type
        self._objects[(bucket, object_key)] = content

    def get(self, bucket: str, object_key: str) -> bytes | None:
        return self._objects.get((bucket, object_key))


@dataclass
class FailingArtifactBlobStore:
    message: str = "MinIO unavailable"

    def put(
        self,
        *,
        bucket: str,
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        raise ArtifactStorageError(self.message)

    def get(self, bucket: str, object_key: str) -> bytes | None:
        return None


class MinioArtifactBlobStore:
    def __init__(
        self,
        *,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        secure: bool | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self._access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self._secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin")
        if secure is None:
            secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        self._secure = secure
        self._timeout = timeout_seconds or float(
            os.getenv("HEALTH_CHECK_TIMEOUT_SECONDS", "2")
        )

    def _client(self) -> tuple[Minio, urllib3.PoolManager]:
        http_client = urllib3.PoolManager(
            timeout=urllib3.Timeout(connect=self._timeout, read=self._timeout),
            retries=False,
        )
        client = Minio(
            self._endpoint,
            access_key=self._access_key,
            secret_key=self._secret_key,
            secure=self._secure,
            http_client=http_client,
        )
        return client, http_client

    def put(
        self,
        *,
        bucket: str,
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        client, http_client = self._client()
        try:
            client.put_object(
                bucket,
                object_key,
                data=io.BytesIO(content),
                length=len(content),
                content_type=content_type,
            )
        except Exception as exc:  # noqa: BLE001
            raise ArtifactStorageError(str(exc)) from exc
        finally:
            http_client.clear()

    def get(self, bucket: str, object_key: str) -> bytes | None:
        client, http_client = self._client()
        try:
            response = client.get_object(bucket, object_key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except Exception:
            return None
        finally:
            http_client.clear()
