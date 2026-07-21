from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.passwords import hash_password
from app.auth.service import (
    AuthService,
    InMemoryOperatorStore,
    OperatorRecord,
    get_auth_service,
    get_blacklist_store,
    InMemoryBlacklistStore,
)
from app.main import app
from app.patients.service import InMemoryPatientStore, PatientService, get_patient_service


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.setenv("JWT_ACCESS_TTL_SECONDS", "900")


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
    patient_service = PatientService(store=patient_store)
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
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_patient_rejects_missing_access_token(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)

    response = client.post("/patients", json={})

    assert response.status_code == 401


def test_create_patient_returns_masked_pac_001(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)

    response = client.post("/patients", headers=headers, json={})

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "PAC-001"
    assert body["has_sensitive_label"] is False
    assert body["sensitive_label_masked"] is None
    assert "sensitive_label" not in body
    assert "sensitive_label_ciphertext" not in body
    assert body["id"]
    assert body["created_at"]
    assert body["updated_at"]


def test_create_patients_assigns_sequential_codes(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)

    first = client.post("/patients", headers=headers, json={})
    second = client.post("/patients", headers=headers, json={})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["code"] == "PAC-001"
    assert second.json()["code"] == "PAC-002"


def test_list_and_get_return_masked_patients(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    created = client.post("/patients", headers=headers, json={}).json()

    listed = client.get("/patients", headers=headers)
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["code"] == "PAC-001"
    assert items[0]["has_sensitive_label"] is False
    assert "sensitive_label" not in items[0]

    detail = client.get(f"/patients/{created['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == created["id"]
    assert detail.json()["code"] == "PAC-001"


def test_get_unknown_patient_returns_404(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)

    response = client.get(
        f"/patients/{uuid.uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Paciente não encontrado"}


def test_patch_does_not_change_patient_code(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    created = client.post("/patients", headers=headers, json={}).json()

    rejected = client.patch(
        f"/patients/{created['id']}",
        headers=headers,
        json={"code": "PAC-999"},
    )
    assert rejected.status_code == 422

    updated = client.patch(
        f"/patients/{created['id']}",
        headers=headers,
        json={},
    )
    assert updated.status_code == 200
    assert updated.json()["code"] == "PAC-001"


def test_delete_patient_removes_resource(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    created = client.post("/patients", headers=headers, json={}).json()

    deleted = client.delete(f"/patients/{created['id']}", headers=headers)
    assert deleted.status_code == 204
    assert deleted.content == b""

    missing = client.get(f"/patients/{created['id']}", headers=headers)
    assert missing.status_code == 404


def test_delete_unknown_patient_returns_404(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)

    response = client.delete(f"/patients/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Paciente não encontrado"}


def test_patient_routes_reject_invalid_token(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    headers = {"Authorization": "Bearer not-a-valid-token"}

    assert client.get("/patients", headers=headers).status_code == 401
    assert client.post("/patients", headers=headers, json={}).status_code == 401
