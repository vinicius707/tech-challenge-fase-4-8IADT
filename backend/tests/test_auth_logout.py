from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth.passwords import hash_password
from app.auth.service import (
    AuthService,
    InMemoryBlacklistStore,
    InMemoryOperatorStore,
    InMemoryRefreshStore,
    OperatorRecord,
    get_auth_service,
    get_blacklist_store,
)
from app.main import app


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.setenv("JWT_ACCESS_TTL_SECONDS", "900")
    monkeypatch.setenv("JWT_REFRESH_TTL_SECONDS", "604800")


@pytest.fixture
def operator_store() -> InMemoryOperatorStore:
    return InMemoryOperatorStore()


@pytest.fixture
def refresh_store() -> InMemoryRefreshStore:
    return InMemoryRefreshStore()


@pytest.fixture
def blacklist_store() -> InMemoryBlacklistStore:
    return InMemoryBlacklistStore()


@pytest.fixture
def client(
    auth_env: None,
    operator_store: InMemoryOperatorStore,
    refresh_store: InMemoryRefreshStore,
    blacklist_store: InMemoryBlacklistStore,
) -> TestClient:
    service = AuthService(
        store=operator_store,
        refresh_store=refresh_store,
        blacklist_store=blacklist_store,
    )
    app.dependency_overrides[get_auth_service] = lambda: service
    app.dependency_overrides[get_blacklist_store] = lambda: blacklist_store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _seed_medico(store: InMemoryOperatorStore) -> OperatorRecord:
    operator = OperatorRecord(
        id=uuid.uuid4(),
        username="medico",
        password_hash=hash_password("medico-secret"),
        role="medico",
    )
    store.save(operator)
    return operator


def _login(client: TestClient) -> dict:
    response = client.post(
        "/auth/login",
        json={"username": "medico", "password": "medico-secret"},
    )
    assert response.status_code == 200
    return response.json()


def test_logout_rejects_missing_access_token(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)

    response = client.post("/auth/logout")

    assert response.status_code == 401


def test_logout_invalidates_access_and_refresh(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    login_body = _login(client)
    access_token = login_body["access_token"]
    refresh_token = login_body["refresh_token"]

    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 204
    assert response.content == b""

    reused_access = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert reused_access.status_code == 401

    reused_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reused_refresh.status_code == 401
    assert reused_refresh.json() == {"detail": "Refresh token inválido"}


def test_logout_rejects_expired_access_token(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_medico(operator_store)
    login_body = _login(client)

    claims = jwt.decode(
        login_body["access_token"],
        "test-secret-not-for-production-32b",
        algorithms=["HS256"],
        options={"verify_exp": False},
    )
    expired = jwt.encode(
        {
            "sub": claims["sub"],
            "username": claims["username"],
            "role": claims["role"],
            "jti": claims["jti"],
            "iat": claims["iat"],
            "exp": datetime.now(tz=UTC) - timedelta(seconds=1),
        },
        "test-secret-not-for-production-32b",
        algorithm="HS256",
    )

    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {expired}"},
    )

    assert response.status_code == 401


def test_logout_rejects_tampered_access_token(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    login_body = _login(client)
    tampered = f"{login_body['access_token']}x"

    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {tampered}"},
    )

    assert response.status_code == 401


def test_logout_revokes_explicit_refresh_token(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    login_body = _login(client)
    access_token = login_body["access_token"]
    refresh_token = login_body["refresh_token"]

    response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 204

    reused_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reused_refresh.status_code == 401
    assert reused_refresh.json() == {"detail": "Refresh token inválido"}
