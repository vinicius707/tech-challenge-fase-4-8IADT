from __future__ import annotations

import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt


@dataclass(frozen=True)
class AuthSettings:
    jwt_secret: str
    access_ttl_seconds: int
    refresh_ttl_seconds: int

    @classmethod
    def from_environment(cls) -> AuthSettings:
        return cls(
            jwt_secret=os.getenv("JWT_SECRET", "change-me-in-development-only"),
            access_ttl_seconds=int(os.getenv("JWT_ACCESS_TTL_SECONDS", "900")),
            refresh_ttl_seconds=int(os.getenv("JWT_REFRESH_TTL_SECONDS", "604800")),
        )


def create_access_token(
    *,
    operator_id: uuid.UUID,
    username: str,
    role: str,
    settings: AuthSettings,
) -> tuple[str, dict[str, Any]]:
    now = datetime.now(tz=UTC)
    claims = {
        "sub": str(operator_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=settings.access_ttl_seconds),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    return token, claims


def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)
