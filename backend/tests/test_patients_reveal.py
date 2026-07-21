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
from app.patients.audit import InMemoryAuditStore
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
def audit_store() -> InMemoryAuditStore:
    return InMemoryAuditStore()


@pytest.fixture
def blacklist_store() -> InMemoryBlacklistStore:
    return InMemoryBlacklistStore()


@pytest.fixture
def client(
    auth_env: None,
    operator_store: InMemoryOperatorStore,
    patient_store: InMemoryPatientStore,
    audit_store: InMemoryAuditStore,
    blacklist_store: InMemoryBlacklistStore,
) -> TestClient:
    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
    patient_service = PatientService(
        store=patient_store,
        audit_store=audit_store,
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


def test_reveal_returns_sensitive_label_and_writes_audit(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    audit_store: InMemoryAuditStore,
) -> None:
    operator = _seed_medico(operator_store)
    headers = _auth_header(client)
    created = client.post(
        "/patients",
        headers=headers,
        json={"sensitive_label": "Paciente Demo"},
    ).json()

    response = client.post(
        f"/patients/{created['id']}/sensitive-label/reveal",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["code"] == "PAC-001"
    assert body["sensitive_label"] == "Paciente Demo"
    assert body["revealed_at"]
    assert "sensitive_label_masked" not in body
    assert "sensitive_label_ciphertext" not in body

    records = audit_store.list_by_patient(uuid.UUID(created["id"]))
    assert len(records) == 1
    assert records[0].action == "reveal_sensitive_label"
    assert records[0].operator_id == operator.id
    assert records[0].patient_id == uuid.UUID(created["id"])


def test_reveal_without_label_returns_404_and_skips_audit(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    audit_store: InMemoryAuditStore,
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    created = client.post("/patients", headers=headers, json={}).json()

    response = client.post(
        f"/patients/{created['id']}/sensitive-label/reveal",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Rótulo Sensível não disponível"}
    assert audit_store.list_by_patient(uuid.UUID(created["id"])) == []


def test_reveal_unknown_patient_returns_404(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)

    response = client.post(
        f"/patients/{uuid.uuid4()}/sensitive-label/reveal",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Paciente não encontrado"}


def test_reveal_rejects_missing_access_token(
    client: TestClient, operator_store: InMemoryOperatorStore
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    created = client.post(
        "/patients",
        headers=headers,
        json={"sensitive_label": "Segredo"},
    ).json()

    response = client.post(f"/patients/{created['id']}/sensitive-label/reveal")

    assert response.status_code == 401


def test_each_reveal_appends_audit_record(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    audit_store: InMemoryAuditStore,
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    created = client.post(
        "/patients",
        headers=headers,
        json={"sensitive_label": "Paciente Demo"},
    ).json()

    first = client.post(
        f"/patients/{created['id']}/sensitive-label/reveal",
        headers=headers,
    )
    second = client.post(
        f"/patients/{created['id']}/sensitive-label/reveal",
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(audit_store.list_by_patient(uuid.UUID(created["id"]))) == 2


def test_delete_patient_cascades_audit_records(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    audit_store: InMemoryAuditStore,
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    created = client.post(
        "/patients",
        headers=headers,
        json={"sensitive_label": "Paciente Demo"},
    ).json()
    client.post(
        f"/patients/{created['id']}/sensitive-label/reveal",
        headers=headers,
    )
    assert len(audit_store.list_by_patient(uuid.UUID(created["id"]))) == 1

    deleted = client.delete(f"/patients/{created['id']}", headers=headers)

    assert deleted.status_code == 204
    assert audit_store.list_by_patient(uuid.UUID(created["id"])) == []
