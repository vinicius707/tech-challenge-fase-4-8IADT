"""TDD T6.15 — POST /cases/{id}/modalities/prescriptions → MinIO + fila `default`."""

from __future__ import annotations

import hashlib
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
from app.outbox.rq_client import DEFAULT_QUEUE_NAME, VIDEO_QUEUE_NAME
from app.outbox.service import InMemoryOutboxStore, OutboxDispatcher, RecordingJobEnqueuer
from app.patients.service import InMemoryPatientStore, PatientService, get_patient_service

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_NORMAL = (
    REPO_ROOT / "data" / "fixtures" / "vitals" / "vitals_normal.csv"
).read_bytes()
RX_NORMAL = (
    REPO_ROOT
    / "data"
    / "fixtures"
    / "prescriptions"
    / "prescriptions_normal.csv"
).read_bytes()
RX_ALT = (
    REPO_ROOT
    / "data"
    / "fixtures"
    / "prescriptions"
    / "prescriptions_medium.csv"
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
def blob_store() -> InMemoryArtifactBlobStore:
    return InMemoryArtifactBlobStore()


@pytest.fixture
def outbox_store() -> InMemoryOutboxStore:
    return InMemoryOutboxStore()


@pytest.fixture
def enqueuer() -> RecordingJobEnqueuer:
    return RecordingJobEnqueuer()


@pytest.fixture
def blacklist_store() -> InMemoryBlacklistStore:
    return InMemoryBlacklistStore()


@pytest.fixture
def client(
    auth_env: None,
    operator_store: InMemoryOperatorStore,
    patient_store: InMemoryPatientStore,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    outbox_store: InMemoryOutboxStore,
    enqueuer: RecordingJobEnqueuer,
    blacklist_store: InMemoryBlacklistStore,
) -> TestClient:
    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
    patient_service = PatientService(store=patient_store, case_store=case_store)
    case_service = CaseService(
        store=case_store,
        patient_store=patient_store,
        blob_store=blob_store,
        outbox_dispatcher=OutboxDispatcher(store=outbox_store, enqueuer=enqueuer),
    )
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_blacklist_store] = lambda: blacklist_store
    app.dependency_overrides[get_patient_service] = lambda: patient_service
    app.dependency_overrides[get_case_service] = lambda: case_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _seed_medico(store: InMemoryOperatorStore) -> None:
    store.save(
        OperatorRecord(
            id=uuid.uuid4(),
            username="medico",
            password_hash=hash_password("medico-secret"),
            role="medico",
        )
    )


def _auth_header(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": "medico", "password": "medico-secret"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_case_with_vitals(client: TestClient, headers: dict[str, str]) -> uuid.UUID:
    patient = client.post("/patients", headers=headers, json={})
    assert patient.status_code == 201
    patient_id = patient.json()["id"]
    created = client.post(
        f"/patients/{patient_id}/cases",
        headers={**headers, "Idempotency-Key": f"vitals-{uuid.uuid4()}"},
        files={"file": ("vitals.csv", VITALS_NORMAL, "text/csv")},
    )
    assert created.status_code == 201
    return uuid.UUID(created.json()["id"])


def test_attach_prescriptions_requires_auth(client: TestClient) -> None:
    response = client.post(
        f"/cases/{uuid.uuid4()}/modalities/prescriptions",
        headers={"Idempotency-Key": "p1"},
        files={"file": ("prescriptions_normal.csv", RX_NORMAL, "text/csv")},
    )
    assert response.status_code == 401


def test_attach_prescriptions_requires_idempotency_key(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    case_id = _create_case_with_vitals(client, headers)
    response = client.post(
        f"/cases/{case_id}/modalities/prescriptions",
        headers=headers,
        files={"file": ("prescriptions_normal.csv", RX_NORMAL, "text/csv")},
    )
    assert response.status_code == 400


def test_attach_prescriptions_unknown_case_returns_404(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_medico(operator_store)
    headers = {
        **_auth_header(client),
        "Idempotency-Key": "missing-case",
    }
    response = client.post(
        f"/cases/{uuid.uuid4()}/modalities/prescriptions",
        headers=headers,
        files={"file": ("prescriptions_normal.csv", RX_NORMAL, "text/csv")},
    )
    assert response.status_code == 404


def test_attach_prescriptions_stores_artifact_and_enqueues_default_queue(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    blob_store: InMemoryArtifactBlobStore,
    enqueuer: RecordingJobEnqueuer,
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    case_id = _create_case_with_vitals(client, headers)
    enqueuer.jobs.clear()

    response = client.post(
        f"/cases/{case_id}/modalities/prescriptions",
        headers={**headers, "Idempotency-Key": "rx-attach-1"},
        files={"file": ("prescriptions_normal.csv", RX_NORMAL, "text/csv")},
    )
    assert response.status_code == 201
    body = response.json()
    modalities = {m["modality"]: m for m in body["modalities"]}
    assert "vitals" in modalities
    assert modalities["prescriptions"]["status"] == "pending"
    assert modalities["prescriptions"]["artifact_id"] is not None

    rx_arts = [a for a in body["artifacts"] if a["modality"] == "prescriptions"]
    assert len(rx_arts) == 1
    art = rx_arts[0]
    digest = hashlib.sha256(RX_NORMAL).hexdigest()
    assert art["content_sha256"] == digest
    assert art["object_key"].startswith(f"cases/{case_id}/prescriptions/")
    assert blob_store.get(art["bucket"], art["object_key"]) == RX_NORMAL

    assert len(enqueuer.jobs) == 1
    job = enqueuer.jobs[0]
    assert job["queue"] == DEFAULT_QUEUE_NAME
    assert job["queue"] != VIDEO_QUEUE_NAME
    assert job["payload"]["modality"] == "prescriptions"
    assert job["payload"]["case_id"] == str(case_id)


def test_attach_prescriptions_idempotent_replay(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    enqueuer: RecordingJobEnqueuer,
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    case_id = _create_case_with_vitals(client, headers)
    key_headers = {**headers, "Idempotency-Key": "rx-replay"}

    first = client.post(
        f"/cases/{case_id}/modalities/prescriptions",
        headers=key_headers,
        files={"file": ("prescriptions_normal.csv", RX_NORMAL, "text/csv")},
    )
    assert first.status_code == 201
    enqueuer.jobs.clear()

    second = client.post(
        f"/cases/{case_id}/modalities/prescriptions",
        headers=key_headers,
        files={"file": ("prescriptions_normal.csv", RX_NORMAL, "text/csv")},
    )
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert enqueuer.jobs == []


def test_attach_prescriptions_idempotency_conflict_different_content(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    case_id = _create_case_with_vitals(client, headers)
    key_headers = {**headers, "Idempotency-Key": "rx-conflict"}

    first = client.post(
        f"/cases/{case_id}/modalities/prescriptions",
        headers=key_headers,
        files={"file": ("prescriptions_normal.csv", RX_NORMAL, "text/csv")},
    )
    assert first.status_code == 201

    conflict = client.post(
        f"/cases/{case_id}/modalities/prescriptions",
        headers=key_headers,
        files={"file": ("prescriptions_medium.csv", RX_ALT, "text/csv")},
    )
    assert conflict.status_code == 409
