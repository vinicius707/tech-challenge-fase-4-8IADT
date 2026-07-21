from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.service import BlacklistStore, get_blacklist_store
from app.auth.tokens import AuthSettings

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AccessTokenClaims:
    sub: UUID
    username: str
    role: str
    jti: str
    exp: datetime
    raw: dict[str, Any]


def decode_access_token(
    token: str, *, settings: AuthSettings | None = None
) -> AccessTokenClaims:
    auth_settings = settings or AuthSettings.from_environment()
    try:
        payload = jwt.decode(
            token,
            auth_settings.jwt_secret,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
        ) from exc

    try:
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        return AccessTokenClaims(
            sub=UUID(payload["sub"]),
            username=payload["username"],
            role=payload["role"],
            jti=payload["jti"],
            exp=exp,
            raw=payload,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
        ) from exc


def get_current_access_claims(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
    blacklist_store: Annotated[BlacklistStore, Depends(get_blacklist_store)],
) -> AccessTokenClaims:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
        )
    claims = decode_access_token(credentials.credentials)
    if blacklist_store.is_blacklisted(claims.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
        )
    return claims
