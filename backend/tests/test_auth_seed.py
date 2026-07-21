from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth.seed import seed_operators
from app.auth.service import (
    AuthService,
    InMemoryOperatorStore,
    get_auth_service,
)
from app.main import app


@pytest.fixture
def seed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.setenv("SEED_MEDICO_USERNAME", "medico")
    monkeypatch.setenv("SEED_MEDICO_PASSWORD", "medico-secret")
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin-secret")


@pytest.fixture
def operator_store() -> InMemoryOperatorStore:
    return InMemoryOperatorStore()


@pytest.fixture
def client(
    seed_env: None, operator_store: InMemoryOperatorStore
) -> TestClient:
    service = AuthService(store=operator_store)
    app.dependency_overrides[get_auth_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_seed_creates_medico_and_admin_operators(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    seed_operators(operator_store)

    medico_login = client.post(
        "/auth/login",
        json={"username": "medico", "password": "medico-secret"},
    )
    assert medico_login.status_code == 200
    assert medico_login.json()["operator"]["role"] == "medico"

    admin_login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin-secret"},
    )
    assert admin_login.status_code == 200
    assert admin_login.json()["operator"]["role"] == "admin"


def test_seed_is_idempotent_and_keeps_operator_identity(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    seed_operators(operator_store)
    first = operator_store.get_by_username("medico")
    assert first is not None

    seed_operators(operator_store)
    second = operator_store.get_by_username("medico")
    assert second is not None
    assert second.id == first.id

    login = client.post(
        "/auth/login",
        json={"username": "medico", "password": "medico-secret"},
    )
    assert login.status_code == 200


def test_seed_updates_password_when_environment_changes(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_operators(operator_store)

    monkeypatch.setenv("SEED_MEDICO_PASSWORD", "novo-segredo")
    seed_operators(operator_store)

    old_password = client.post(
        "/auth/login",
        json={"username": "medico", "password": "medico-secret"},
    )
    assert old_password.status_code == 401

    new_password = client.post(
        "/auth/login",
        json={"username": "medico", "password": "novo-segredo"},
    )
    assert new_password.status_code == 200


def test_seed_stores_only_bcrypt_hashes(
    seed_env: None, operator_store: InMemoryOperatorStore
) -> None:
    seed_operators(operator_store)

    for username in ("medico", "admin"):
        operator = operator_store.get_by_username(username)
        assert operator is not None
        assert operator.password_hash.startswith("$2")
        assert "secret" not in operator.password_hash


def test_seed_skips_when_credentials_are_missing(
    operator_store: InMemoryOperatorStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SEED_MEDICO_USERNAME", raising=False)
    monkeypatch.delenv("SEED_MEDICO_PASSWORD", raising=False)
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin-secret")

    seed_operators(operator_store)

    assert operator_store.get_by_username("medico") is None
    assert operator_store.get_by_username("admin") is not None
