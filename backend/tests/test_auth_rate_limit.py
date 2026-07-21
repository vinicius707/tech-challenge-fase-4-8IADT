from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.passwords import hash_password
from app.auth.rate_limit import LoginRateLimiter, get_login_rate_limiter
from app.auth.service import (
    AuthService,
    InMemoryOperatorStore,
    OperatorRecord,
    get_auth_service,
)
from app.main import app


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.setenv("JWT_ACCESS_TTL_SECONDS", "900")
    monkeypatch.setenv("AUTH_LOGIN_RATE_LIMIT", "5/minute")


@pytest.fixture
def operator_store() -> InMemoryOperatorStore:
    return InMemoryOperatorStore()


@pytest.fixture
def rate_limiter() -> LoginRateLimiter:
    return LoginRateLimiter.from_environment()


@pytest.fixture
def client(
    auth_env: None,
    operator_store: InMemoryOperatorStore,
    rate_limiter: LoginRateLimiter,
) -> TestClient:
    service = AuthService(store=operator_store)
    app.dependency_overrides[get_auth_service] = lambda: service
    app.dependency_overrides[get_login_rate_limiter] = lambda: rate_limiter
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


def test_login_within_limit_is_not_rate_limited(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)

    for _ in range(5):
        response = client.post(
            "/auth/login",
            json={"username": "medico", "password": "medico-secret"},
        )
        assert response.status_code == 200


def test_login_beyond_limit_returns_429_even_with_valid_password(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)

    for _ in range(5):
        client.post(
            "/auth/login",
            json={"username": "medico", "password": "wrong-password"},
        )

    response = client.post(
        "/auth/login",
        json={"username": "medico", "password": "medico-secret"},
    )

    assert response.status_code == 429
    assert response.json() == {
        "detail": "Muitas tentativas de login. Tente novamente mais tarde."
    }


def test_rate_limit_window_resets_after_expiry(auth_env: None) -> None:
    now = [1000.0]
    limiter = LoginRateLimiter(limit=2, window_seconds=60, clock=lambda: now[0])

    assert limiter.try_acquire("10.0.0.1")
    assert limiter.try_acquire("10.0.0.1")
    assert not limiter.try_acquire("10.0.0.1")

    now[0] += 61.0
    assert limiter.try_acquire("10.0.0.1")


def test_rate_limit_is_tracked_per_originator(auth_env: None) -> None:
    limiter = LoginRateLimiter(limit=1, window_seconds=60, clock=lambda: 1000.0)

    assert limiter.try_acquire("10.0.0.1")
    assert not limiter.try_acquire("10.0.0.1")
    assert limiter.try_acquire("10.0.0.2")
