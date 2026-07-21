from __future__ import annotations

import uuid

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.auth.passwords import hash_password
from app.auth.service import (
    AuthService,
    InMemoryBlacklistStore,
    InMemoryOperatorStore,
    OperatorRecord,
    get_auth_service,
    get_blacklist_store,
)
from app.main import app
from app.patients.crypto import SensitiveLabelCipher
from app.patients.service import InMemoryPatientStore, PatientService, get_patient_service

TEST_PII_KEY = Fernet.generate_key().decode()


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.setenv("JWT_ACCESS_TTL_SECONDS", "900")
    monkeypatch.setenv("PII_ENCRYPTION_KEY", TEST_PII_KEY)


@pytest.fixture
def operator_store() -> InMemoryOperatorStore:
    return InMemoryOperatorStore()


@pytest.fixture
def patient_store() -> InMemoryPatientStore:
    return InMemoryPatientStore()


@pytest.fixture
def blacklist_store() -> InMemoryBlacklistStore:
    return InMemoryBlacklistStore()


@pytest.fixture
def client(
    auth_env: None,
    operator_store: InMemoryOperatorStore,
    patient_store: InMemoryPatientStore,
    blacklist_store: InMemoryBlacklistStore,
) -> TestClient:
    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
    patient_service = PatientService(
        store=patient_store,
        cipher=SensitiveLabelCipher.from_environment(),
    )
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_blacklist_store] = lambda: blacklist_store
    app.dependency_overrides[get_patient_service] = lambda: patient_service
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


def _auth_header(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": "medico", "password": "medico-secret"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_create_patient_with_label_returns_masked_response(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    patient_store: InMemoryPatientStore,
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)

    response = client.post(
        "/patients",
        headers=headers,
        json={"sensitive_label": "Paciente Demo"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "PAC-001"
    assert body["has_sensitive_label"] is True
    assert body["sensitive_label_masked"] == "********"
    assert "sensitive_label" not in body
    assert "Paciente Demo" not in response.text
    assert "sensitive_label_ciphertext" not in body

    stored = patient_store.get_by_id(uuid.UUID(body["id"]))
    assert stored is not None
    assert stored.sensitive_label_ciphertext is not None
    assert stored.sensitive_label_ciphertext != "Paciente Demo"
    assert "Paciente Demo" not in stored.sensitive_label_ciphertext


def test_create_without_label_still_works_without_pii_key(
    operator_store: InMemoryOperatorStore,
    patient_store: InMemoryPatientStore,
    blacklist_store: InMemoryBlacklistStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.delenv("PII_ENCRYPTION_KEY", raising=False)
    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
    patient_service = PatientService(
        store=patient_store,
        cipher=SensitiveLabelCipher.from_environment(),
    )
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_blacklist_store] = lambda: blacklist_store
    app.dependency_overrides[get_patient_service] = lambda: patient_service
    _seed_medico(operator_store)

    with TestClient(app) as client:
        headers = _auth_header(client)
        ok = client.post("/patients", headers=headers, json={})
        assert ok.status_code == 201
        assert ok.json()["has_sensitive_label"] is False

        blocked = client.post(
            "/patients",
            headers=headers,
            json={"sensitive_label": "Segredo"},
        )
        assert blocked.status_code == 503
        assert blocked.json() == {
            "detail": "Criptografia de Rótulo Sensível indisponível"
        }
        assert "Segredo" not in blocked.text

    app.dependency_overrides.clear()


def test_patch_updates_and_removes_sensitive_label(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    patient_store: InMemoryPatientStore,
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    created = client.post("/patients", headers=headers, json={}).json()

    updated = client.patch(
        f"/patients/{created['id']}",
        headers=headers,
        json={"sensitive_label": "Novo Rótulo"},
    )
    assert updated.status_code == 200
    assert updated.json()["has_sensitive_label"] is True
    assert updated.json()["sensitive_label_masked"] == "********"
    assert "Novo Rótulo" not in updated.text

    stored = patient_store.get_by_id(uuid.UUID(created["id"]))
    assert stored is not None
    assert stored.sensitive_label_ciphertext is not None
    first_ciphertext = stored.sensitive_label_ciphertext

    replaced = client.patch(
        f"/patients/{created['id']}",
        headers=headers,
        json={"sensitive_label": "Outro"},
    )
    assert replaced.status_code == 200
    stored_again = patient_store.get_by_id(uuid.UUID(created["id"]))
    assert stored_again is not None
    assert stored_again.sensitive_label_ciphertext != first_ciphertext

    cleared = client.patch(
        f"/patients/{created['id']}",
        headers=headers,
        json={"sensitive_label": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["has_sensitive_label"] is False
    assert cleared.json()["sensitive_label_masked"] is None
    stored_cleared = patient_store.get_by_id(uuid.UUID(created["id"]))
    assert stored_cleared is not None
    assert stored_cleared.sensitive_label_ciphertext is None


def test_empty_sensitive_label_is_treated_as_absent(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)

    response = client.post(
        "/patients",
        headers=headers,
        json={"sensitive_label": "   "},
    )

    assert response.status_code == 201
    assert response.json()["has_sensitive_label"] is False


def test_list_and_get_keep_label_masked(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    created = client.post(
        "/patients",
        headers=headers,
        json={"sensitive_label": "Nome Oculto"},
    ).json()

    listed = client.get("/patients", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["sensitive_label_masked"] == "********"
    assert "Nome Oculto" not in listed.text

    detail = client.get(f"/patients/{created['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["has_sensitive_label"] is True
    assert "Nome Oculto" not in detail.text


def test_fernet_roundtrip_unit() -> None:
    key = Fernet.generate_key().decode()
    cipher = SensitiveLabelCipher(_fernet=Fernet(key.encode("utf-8")))
    token = cipher.encrypt("rótulo de teste")
    assert token != "rótulo de teste"
    assert cipher.decrypt(token) == "rótulo de teste"
