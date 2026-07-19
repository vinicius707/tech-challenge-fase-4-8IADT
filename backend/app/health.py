import math
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

import psycopg
import urllib3
from minio import Minio
from redis import Redis

CheckStatus = Literal["ok", "error"]
OverallStatus = Literal["ok", "error"]
DependencyCheck = Callable[[], bool]


@dataclass(frozen=True)
class HealthSettings:
    postgres_url: str
    redis_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool
    timeout_seconds: float

    @classmethod
    def from_environment(cls) -> "HealthSettings":
        return cls(
            postgres_url=os.getenv(
                "POSTGRES_URL",
                "postgresql://limen:limen@localhost:5432/limen",
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            minio_endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            minio_bucket=os.getenv("MINIO_BUCKET", "limen"),
            minio_secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
            timeout_seconds=float(os.getenv("HEALTH_CHECK_TIMEOUT_SECONDS", "2")),
        )


@dataclass(frozen=True)
class HealthReport:
    status: OverallStatus
    checks: dict[str, CheckStatus]

    @property
    def status_code(self) -> int:
        return 200 if self.status == "ok" else 503

    def as_dict(self) -> dict[str, object]:
        return {"status": self.status, "checks": self.checks}


class HealthService:
    def __init__(self, checks: Mapping[str, DependencyCheck]) -> None:
        self._checks = checks

    def check(self) -> HealthReport:
        results = {
            name: self._run_check(check)
            for name, check in self._checks.items()
        }
        status: OverallStatus = (
            "ok" if all(result == "ok" for result in results.values()) else "error"
        )
        return HealthReport(status=status, checks=results)

    @staticmethod
    def _run_check(check: DependencyCheck) -> CheckStatus:
        try:
            return "ok" if check() else "error"
        except Exception:
            return "error"


def get_health_service() -> HealthService:
    settings = HealthSettings.from_environment()
    return HealthService(
        {
            "postgres": lambda: _check_postgres(settings),
            "redis": lambda: _check_redis(settings),
            "minio": lambda: _check_minio(settings),
        }
    )


def _check_postgres(settings: HealthSettings) -> bool:
    connect_timeout = max(1, math.ceil(settings.timeout_seconds))
    with psycopg.connect(
        settings.postgres_url,
        connect_timeout=connect_timeout,
        autocommit=True,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)


def _check_redis(settings: HealthSettings) -> bool:
    client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.timeout_seconds,
        socket_timeout=settings.timeout_seconds,
    )
    try:
        return bool(client.ping())
    finally:
        client.close()


def _check_minio(settings: HealthSettings) -> bool:
    http_client = urllib3.PoolManager(
        timeout=urllib3.Timeout(
            connect=settings.timeout_seconds,
            read=settings.timeout_seconds,
        ),
        retries=False,
    )
    try:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            http_client=http_client,
        )
        return client.bucket_exists(settings.minio_bucket)
    finally:
        http_client.clear()
