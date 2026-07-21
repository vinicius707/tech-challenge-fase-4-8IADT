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
    family_id: uuid.UUID
    expires_at: datetime
    revoked: bool = False


class OperatorStore(Protocol):
    def get_by_username(self, username: str) -> OperatorRecord | None: ...

    def get_by_id(self, operator_id: uuid.UUID) -> OperatorRecord | None: ...

    def save(self, operator: OperatorRecord) -> None: ...


class RefreshStore(Protocol):
    def save(self, record: RefreshRecord) -> None: ...

    def get_by_hash(self, token_hash: str) -> RefreshRecord | None: ...

    def get_by_access_jti(self, access_jti: str) -> RefreshRecord | None: ...

    def revoke(self, token_hash: str) -> None: ...

    def revoke_family(self, family_id: uuid.UUID) -> None: ...


class BlacklistStore(Protocol):
    def add(self, jti: str, expires_at: datetime) -> None: ...

    def is_blacklisted(self, jti: str) -> bool: ...


@dataclass
class InMemoryOperatorStore:
    _operators_by_username: dict[str, OperatorRecord] = field(default_factory=dict)
    _operators_by_id: dict[uuid.UUID, OperatorRecord] = field(default_factory=dict)

    def get_by_username(self, username: str) -> OperatorRecord | None:
        return self._operators_by_username.get(username)

    def get_by_id(self, operator_id: uuid.UUID) -> OperatorRecord | None:
        return self._operators_by_id.get(operator_id)

    def save(self, operator: OperatorRecord) -> None:
        self._operators_by_username[operator.username] = operator
        self._operators_by_id[operator.id] = operator


@dataclass
class InMemoryRefreshStore:
    _tokens: dict[str, RefreshRecord] = field(default_factory=dict)

    def save(self, record: RefreshRecord) -> None:
        self._tokens[record.token_hash] = record

    def get_by_hash(self, token_hash: str) -> RefreshRecord | None:
        return self._tokens.get(token_hash)

    def get_by_access_jti(self, access_jti: str) -> RefreshRecord | None:
        for record in self._tokens.values():
            if record.access_jti == access_jti and not record.revoked:
                return record
        return None

    def revoke(self, token_hash: str) -> None:
        record = self._tokens.get(token_hash)
        if record is not None:
            record.revoked = True

    def revoke_family(self, family_id: uuid.UUID) -> None:
        for record in self._tokens.values():
            if record.family_id == family_id:
                record.revoked = True


@dataclass
class InMemoryBlacklistStore:
    _entries: dict[str, datetime] = field(default_factory=dict)

    def add(self, jti: str, expires_at: datetime) -> None:
        self._entries[jti] = expires_at

    def is_blacklisted(self, jti: str) -> bool:
        expires_at = self._entries.get(jti)
        if expires_at is None:
            return False
        if expires_at <= datetime.now(tz=UTC):
            del self._entries[jti]
            return False
        return True


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(
        self,
        *,
        store: OperatorStore,
        refresh_store: RefreshStore | None = None,
        blacklist_store: BlacklistStore | None = None,
        settings: AuthSettings | None = None,
    ) -> None:
        self._store = store
        self._refresh_store = refresh_store or InMemoryRefreshStore()
        self._blacklist_store = blacklist_store or InMemoryBlacklistStore()
        self._settings = settings or AuthSettings.from_environment()

    def login(self, *, username: str, password: str) -> LoginResponse | None:
        operator = self._store.get_by_username(username)
        if operator is None or not verify_password(password, operator.password_hash):
            return None
        return self._issue_tokens(operator, family_id=uuid.uuid4())

    def refresh(self, *, refresh_token: str) -> LoginResponse | None:
        token_hash = hash_refresh_token(refresh_token)
        record = self._refresh_store.get_by_hash(token_hash)
        if record is None:
            return None

        if record.revoked:
            self._refresh_store.revoke_family(record.family_id)
            return None

        if record.expires_at <= datetime.now(tz=UTC):
            self._refresh_store.revoke(token_hash)
            return None

        operator = self._store.get_by_id(record.operator_id)
        if operator is None:
            self._refresh_store.revoke_family(record.family_id)
            return None

        self._refresh_store.revoke(token_hash)
        return self._issue_tokens(operator, family_id=record.family_id)

    def logout(
        self,
        *,
        jti: str,
        exp: datetime,
        operator_id: uuid.UUID,
        refresh_token: str | None = None,
    ) -> None:
        self._blacklist_store.add(jti, exp)

        if refresh_token is not None:
            token_hash = hash_refresh_token(refresh_token)
            record = self._refresh_store.get_by_hash(token_hash)
            if record is not None and record.operator_id == operator_id:
                self._refresh_store.revoke(token_hash)
                return

        linked = self._refresh_store.get_by_access_jti(jti)
        if linked is not None and linked.operator_id == operator_id:
            self._refresh_store.revoke(linked.token_hash)

    def _issue_tokens(
        self, operator: OperatorRecord, *, family_id: uuid.UUID
    ) -> LoginResponse:
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
                family_id=family_id,
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
_default_blacklist_store = InMemoryBlacklistStore()


def get_auth_service() -> AuthService:
    return AuthService(
        store=_default_store,
        refresh_store=_default_refresh_store,
        blacklist_store=_default_blacklist_store,
    )


def get_blacklist_store() -> BlacklistStore:
    return _default_blacklist_store


def get_operator_store() -> OperatorStore:
    return _default_store
