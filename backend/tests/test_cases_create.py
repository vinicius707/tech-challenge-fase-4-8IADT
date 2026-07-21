"""TDD T3.6 — Caso real + Idempotency-Key (sem MinIO/AnomalyEngine)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
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
from app.cases.service import CaseService, InMemoryCaseStore, get_case_service
from app.cases.storage import InMemoryArtifactBlobStore
from app.main import app
from app.outbox.service import InMemoryOutboxStore, OutboxDispatcher, RecordingJobEnqueuer
from app.patients.service import InMemoryPatientStore, PatientService, get_patient_service

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_NORMAL = (
    REPO_ROOT / "data" / "fixtures" / "vitals" / "vitals_normal.csv"
).read_bytes()


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
def case_store() -> InMemoryCaseStore:
    return InMemoryCaseStore()


@pytest.fixture
def blacklist_store() -> InMemoryBlacklistStore:
    return InMemoryBlacklistStore()


@pytest.fixture
def client(
    auth_env: None,
    operator_store: InMemoryOperatorStore,
    patient_store: InMemoryPatientStore,
    case_store: InMemoryCaseStore,
    blacklist_store: InMemoryBlacklistStore,
) -> TestClient:
    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
    patient_service = PatientService(store=patient_store, case_store=case_store)
    case_service = CaseService(
        store=case_store,
        patient_store=patient_store,
        blob_store=InMemoryArtifactBlobStore(),
        outbox_dispatcher=OutboxDispatcher(
            store=InMemoryOutboxStore(),
            enqueuer=RecordingJobEnqueuer(),
        ),
    )
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_blacklist_store] = lambda: blacklist_store
    app.dependency_overrides[get_patient_service] = lambda: patient_service
    app.dependency_overrides[get_case_service] = lambda: case_service
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


def _create_patient(client: TestClient, headers: dict[str, str]) -> uuid.UUID:
    created = client.post("/patients", headers=headers, json={})
    assert created.status_code == 201
    return uuid.UUID(created.json()["id"])


def test_create_case_requires_auth(client: TestClient) -> None:
    response = client.post(
        f"/patients/{uuid.uuid4()}/cases",
        headers={"Idempotency-Key": "k1"},
        files={"file": ("vitals.csv", VITALS_NORMAL, "text/csv")},
    )
    assert response.status_code == 401


def test_get_case_requires_auth(client: TestClient) -> None:
    response = client.get(f"/cases/{uuid.uuid4()}")
    assert response.status_code == 401


def test_create_case_patient_not_found(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_medico(operator_store)
    headers = {**_auth_header(client), "Idempotency-Key": "missing-patient"}
    response = client.post(
        f"/patients/{uuid.uuid4()}/cases",
        headers=headers,
        files={"file": ("vitals.csv", VITALS_NORMAL, "text/csv")},
    )
    assert response.status_code == 404


def test_create_case_requires_idempotency_key(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    patient_id = _create_patient(client, headers)
    response = client.post(
        f"/patients/{patient_id}/cases",
        headers=headers,
        files={"file": ("vitals.csv", VITALS_NORMAL, "text/csv")},
    )
    assert response.status_code == 400


def test_create_case_returns_201_pending(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_medico(operator_store)
    headers = {**_auth_header(client), "Idempotency-Key": "create-1"}
    patient_id = _create_patient(client, headers)
    response = client.post(
        f"/patients/{patient_id}/cases",
        headers=headers,
        files={"file": ("vitals.csv", VITALS_NORMAL, "text/csv")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["patient_id"] == str(patient_id)
    assert body["status"] == "pending"
    assert body["risk_score"] is None
    assert body["risk_level"] is None
    assert len(body["modalities"]) == 1
    assert body["modalities"][0]["modality"] == "vitals"
    assert body["modalities"][0]["status"] == "pending"
    assert body["modalities"][0]["artifact_id"] is not None


def test_create_case_idempotent_same_key_and_content(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_medico(operator_store)
    headers = {**_auth_header(client), "Idempotency-Key": "idem-same"}
    patient_id = _create_patient(client, headers)
    first = client.post(
        f"/patients/{patient_id}/cases",
        headers=headers,
        files={"file": ("vitals.csv", VITALS_NORMAL, "text/csv")},
    )
    second = client.post(
        f"/patients/{patient_id}/cases",
        headers=headers,
        files={"file": ("vitals.csv", VITALS_NORMAL, "text/csv")},
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_create_case_idempotency_conflict_different_content(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_medico(operator_store)
    headers = {**_auth_header(client), "Idempotency-Key": "idem-conflict"}
    patient_id = _create_patient(client, headers)
    first = client.post(
        f"/patients/{patient_id}/cases",
        headers=headers,
        files={"file": ("vitals.csv", VITALS_NORMAL, "text/csv")},
    )
    assert first.status_code == 201
    conflict = client.post(
        f"/patients/{patient_id}/cases",
        headers=headers,
        files={"file": ("vitals.csv", b"timestamp,heart_rate\n0,999\n", "text/csv")},
    )
    assert conflict.status_code == 409


def test_get_case_returns_created(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_medico(operator_store)
    headers = {**_auth_header(client), "Idempotency-Key": "get-1"}
    patient_id = _create_patient(client, headers)
    created = client.post(
        f"/patients/{patient_id}/cases",
        headers=headers,
        files={"file": ("vitals.csv", VITALS_NORMAL, "text/csv")},
    ).json()
    response = client.get(f"/cases/{created['id']}", headers=_auth_header(client))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["status"] == "pending"
    assert body["modalities"][0]["modality"] == "vitals"


def test_get_case_not_found(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_medico(operator_store)
    response = client.get(f"/cases/{uuid.uuid4()}", headers=_auth_header(client))
    assert response.status_code == 404


def test_case_model_schema_and_cascade_fk() -> None:
    from sqlalchemy import inspect

    import app.patients.models  # noqa: F401
    from app.cases.models import Artifact, Case, CaseModality

    case_cols = {c.key for c in inspect(Case).mapper.column_attrs}
    assert case_cols >= {
        "id",
        "patient_id",
        "status",
        "risk_score",
        "risk_level",
        "idempotency_key",
        "content_sha256",
        "created_at",
        "updated_at",
    }
    fk = next(iter(inspect(Case).mapper.columns["patient_id"].foreign_keys))
    assert fk.column.table.name == "patients"
    assert fk.ondelete == "CASCADE"

    modality_cols = {c.key for c in inspect(CaseModality).mapper.column_attrs}
    assert modality_cols >= {"case_id", "modality", "status", "artifact_id"}

    artifact_cols = {c.key for c in inspect(Artifact).mapper.column_attrs}
    assert artifact_cols >= {
        "id",
        "case_id",
        "modality",
        "bucket",
        "object_key",
        "content_sha256",
        "content_type",
    }
