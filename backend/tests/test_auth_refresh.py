from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth.passwords import hash_password
from app.auth.service import (
    AuthService,
    InMemoryOperatorStore,
    InMemoryRefreshStore,
    OperatorRecord,
    get_auth_service,
    hash_refresh_token,
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
def client(
    auth_env: None,
    operator_store: InMemoryOperatorStore,
    refresh_store: InMemoryRefreshStore,
) -> TestClient:
    service = AuthService(store=operator_store, refresh_store=refresh_store)
    app.dependency_overrides[get_auth_service] = lambda: service
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


def test_refresh_rotates_access_and_refresh_tokens(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    operator = _seed_medico(operator_store)
    login_body = _login(client)
    old_refresh = login_body["refresh_token"]
    old_access = login_body["access_token"]

    response = client.post("/auth/refresh", json={"refresh_token": old_refresh})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["operator"] == {
        "id": str(operator.id),
        "username": "medico",
        "role": "medico",
    }
    assert body["access_token"] != old_access
    assert body["refresh_token"] != old_refresh

    claims = jwt.decode(
        body["access_token"],
        "test-secret-not-for-production-32b",
        algorithms=["HS256"],
    )
    assert claims["sub"] == str(operator.id)
    assert claims["role"] == "medico"
    assert "jti" in claims

    reused = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401
    assert reused.json() == {"detail": "Refresh token inválido"}


def test_refresh_rejects_unknown_token(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "totally-unknown-refresh-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Refresh token inválido"}


def test_refresh_reuse_invalidates_session_family(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    login_body = _login(client)
    first_refresh = login_body["refresh_token"]

    rotated = client.post("/auth/refresh", json={"refresh_token": first_refresh})
    assert rotated.status_code == 200
    second_refresh = rotated.json()["refresh_token"]

    reuse = client.post("/auth/refresh", json={"refresh_token": first_refresh})
    assert reuse.status_code == 401
    assert reuse.json() == {"detail": "Refresh token inválido"}

    follow_up = client.post("/auth/refresh", json={"refresh_token": second_refresh})
    assert follow_up.status_code == 401
    assert follow_up.json() == {"detail": "Refresh token inválido"}


def test_refresh_rejects_expired_token(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    refresh_store: InMemoryRefreshStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_REFRESH_TTL_SECONDS", "1")
    service = AuthService(
        store=operator_store,
        refresh_store=refresh_store,
    )
    app.dependency_overrides[get_auth_service] = lambda: service
    _seed_medico(operator_store)

    login_body = _login(client)
    refresh_token = login_body["refresh_token"]
    record = refresh_store.get_by_hash(hash_refresh_token(refresh_token))
    assert record is not None
    record.expires_at = datetime.now(tz=UTC) - timedelta(seconds=1)

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 401
    assert response.json() == {"detail": "Refresh token inválido"}
