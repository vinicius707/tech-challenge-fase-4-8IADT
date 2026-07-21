from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth.passwords import hash_password, verify_password
from app.auth.service import (
    AuthService,
    InMemoryOperatorStore,
    OperatorRecord,
    get_auth_service,
)
from app.main import app

Role = Literal["medico", "admin"]


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.setenv("JWT_ACCESS_TTL_SECONDS", "900")


@pytest.fixture
def operator_store() -> InMemoryOperatorStore:
    return InMemoryOperatorStore()


@pytest.fixture
def client(
    auth_env: None, operator_store: InMemoryOperatorStore
) -> TestClient:
    service = AuthService(store=operator_store)
    app.dependency_overrides[get_auth_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _seed(
    store: InMemoryOperatorStore, *, username: str, password: str, role: Role
) -> OperatorRecord:
    operator = OperatorRecord(
        id=uuid.uuid4(),
        username=username,
        password_hash=hash_password(password),
        role=role,
    )
    store.save(operator)
    return operator


def test_password_is_stored_with_bcrypt() -> None:
    hashed = hash_password("medico-secret")

    assert hashed != "medico-secret"
    assert hashed.startswith("$2")
    assert verify_password("medico-secret", hashed)
    assert not verify_password("wrong-password", hashed)


def test_login_returns_access_token_for_medico(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    operator = _seed(
        operator_store, username="medico", password="medico-secret", role="medico"
    )

    response = client.post(
        "/auth/login",
        json={"username": "medico", "password": "medico-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["operator"] == {
        "id": str(operator.id),
        "username": "medico",
        "role": "medico",
    }
    assert "password" not in body
    assert "password_hash" not in body["operator"]
    assert body["access_token"]
    assert body["refresh_token"]

    claims = jwt.decode(
        body["access_token"],
        "test-secret-not-for-production-32b",
        algorithms=["HS256"],
    )
    assert claims["sub"] == str(operator.id)
    assert claims["username"] == "medico"
    assert claims["role"] == "medico"
    assert "jti" in claims
    assert "exp" in claims
    assert "iat" in claims
    assert datetime.fromtimestamp(claims["exp"], tz=UTC) - datetime.fromtimestamp(
        claims["iat"], tz=UTC
    ) == timedelta(seconds=900)


def test_login_returns_access_token_for_admin(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed(operator_store, username="admin", password="admin-secret", role="admin")

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin-secret"},
    )

    assert response.status_code == 200
    assert response.json()["operator"]["role"] == "admin"


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("medico", "wrong-password"),
        ("unknown", "medico-secret"),
    ],
)
def test_login_rejects_invalid_credentials_generically(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    username: str,
    password: str,
) -> None:
    _seed(operator_store, username="medico", password="medico-secret", role="medico")

    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciais inválidas"}
    assert "$2" not in response.text
    assert "password_hash" not in response.text
