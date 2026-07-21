from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.auth.passwords import verify_password
from app.auth.schemas import LoginResponse, OperatorResponse
from app.auth.tokens import AuthSettings, create_access_token, create_refresh_token


@dataclass(frozen=True)
class OperatorRecord:
    id: uuid.UUID
    username: str
    password_hash: str
    role: str


@dataclass
class RefreshRecord:
    token_hash: str
    operator_id: uuid.UUID
    access_jti: str
    expires_at: datetime
    revoked: bool = False


class OperatorStore(Protocol):
    def get_by_username(self, username: str) -> OperatorRecord | None: ...

    def save(self, operator: OperatorRecord) -> None: ...


class RefreshStore(Protocol):
    def save(self, record: RefreshRecord) -> None: ...


@dataclass
class InMemoryOperatorStore:
    _operators: dict[str, OperatorRecord] = field(default_factory=dict)

    def get_by_username(self, username: str) -> OperatorRecord | None:
        return self._operators.get(username)

    def save(self, operator: OperatorRecord) -> None:
        self._operators[operator.username] = operator


@dataclass
class InMemoryRefreshStore:
    _tokens: dict[str, RefreshRecord] = field(default_factory=dict)

    def save(self, record: RefreshRecord) -> None:
        self._tokens[record.token_hash] = record


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(
        self,
        *,
        store: OperatorStore,
        refresh_store: RefreshStore | None = None,
        settings: AuthSettings | None = None,
    ) -> None:
        self._store = store
        self._refresh_store = refresh_store or InMemoryRefreshStore()
        self._settings = settings or AuthSettings.from_environment()

    def login(self, *, username: str, password: str) -> LoginResponse | None:
        operator = self._store.get_by_username(username)
        if operator is None or not verify_password(password, operator.password_hash):
            return None

        access_token, claims = create_access_token(
            operator_id=operator.id,
            username=operator.username,
            role=operator.role,
            settings=self._settings,
        )
        refresh_token = create_refresh_token()
        self._refresh_store.save(
            RefreshRecord(
                token_hash=hash_refresh_token(refresh_token),
                operator_id=operator.id,
                access_jti=str(claims["jti"]),
                expires_at=datetime.now(tz=UTC)
                + timedelta(seconds=self._settings.refresh_ttl_seconds),
            )
        )
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._settings.access_ttl_seconds,
            operator=OperatorResponse(
                id=operator.id,
                username=operator.username,
                role=operator.role,  # type: ignore[arg-type]
            ),
        )


_default_store = InMemoryOperatorStore()
_default_refresh_store = InMemoryRefreshStore()


def get_auth_service() -> AuthService:
    return AuthService(store=_default_store, refresh_store=_default_refresh_store)
