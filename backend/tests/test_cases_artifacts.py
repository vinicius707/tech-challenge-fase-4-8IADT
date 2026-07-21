"""TDD T3.7 — Artefato no object store + outbox/enqueue no create do Caso."""

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
from app.cases.storage import (
    ArtifactStorageError,
    FailingArtifactBlobStore,
    InMemoryArtifactBlobStore,
)
from app.main import app
from app.outbox.service import (
    InMemoryOutboxStore,
    OutboxDispatcher,
    RecordingJobEnqueuer,
)
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
def blob_store() -> InMemoryArtifactBlobStore:
    return InMemoryArtifactBlobStore()


@pytest.fixture
def outbox_store() -> InMemoryOutboxStore:
    return InMemoryOutboxStore()


@pytest.fixture
def enqueuer() -> RecordingJobEnqueuer:
    return RecordingJobEnqueuer(queue_name="default")


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
    dispatcher = OutboxDispatcher(store=outbox_store, enqueuer=enqueuer)
    case_service = CaseService(
        store=case_store,
        patient_store=patient_store,
        blob_store=blob_store,
        outbox_dispatcher=dispatcher,
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


def test_create_case_uploads_artifact_and_enqueues_outbox(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    blob_store: InMemoryArtifactBlobStore,
    outbox_store: InMemoryOutboxStore,
    enqueuer: RecordingJobEnqueuer,
) -> None:
    _seed_medico(operator_store)
    headers = {**_auth_header(client), "Idempotency-Key": "art-1"}
    patient_id = _create_patient(client, headers)

    response = client.post(
        f"/patients/{patient_id}/cases",
        headers=headers,
        files={"file": ("vitals.csv", VITALS_NORMAL, "text/csv")},
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body["artifacts"]) == 1
    artifact = body["artifacts"][0]
    assert artifact["bucket"] == "limen"
    assert artifact["object_key"].startswith(f"cases/{body['id']}/vitals/")
    assert blob_store.get(artifact["bucket"], artifact["object_key"]) == VITALS_NORMAL

    jobs = list(outbox_store._by_id.values())
    assert len(jobs) == 1
    assert jobs[0].aggregate_type == "case"
    assert jobs[0].aggregate_id == uuid.UUID(body["id"])
    assert jobs[0].payload["modality"] == "vitals"
    assert jobs[0].status == "enqueued"
    assert jobs[0].rq_job_id is not None
    assert len(enqueuer.jobs) == 1
    assert enqueuer.jobs[0]["queue"] == "default"


def test_create_case_minio_unavailable_returns_503_without_case(
    auth_env: None,
    operator_store: InMemoryOperatorStore,
    patient_store: InMemoryPatientStore,
    case_store: InMemoryCaseStore,
    outbox_store: InMemoryOutboxStore,
    blacklist_store: InMemoryBlacklistStore,
) -> None:
    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
    patient_service = PatientService(store=patient_store, case_store=case_store)
    dispatcher = OutboxDispatcher(
        store=outbox_store, enqueuer=RecordingJobEnqueuer()
    )
    case_service = CaseService(
        store=case_store,
        patient_store=patient_store,
        blob_store=FailingArtifactBlobStore(),
        outbox_dispatcher=dispatcher,
    )
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_blacklist_store] = lambda: blacklist_store
    app.dependency_overrides[get_patient_service] = lambda: patient_service
    app.dependency_overrides[get_case_service] = lambda: case_service
    try:
        with TestClient(app) as client:
            _seed_medico(operator_store)
            headers = {**_auth_header(client), "Idempotency-Key": "minio-down"}
            patient_id = _create_patient(client, headers)
            response = client.post(
                f"/patients/{patient_id}/cases",
                headers=headers,
                files={"file": ("vitals.csv", VITALS_NORMAL, "text/csv")},
            )
            assert response.status_code == 503
            assert case_store._by_id == {}
            assert outbox_store._by_id == {}
    finally:
        app.dependency_overrides.clear()


def test_idempotent_replay_does_not_duplicate_artifact_or_outbox(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    blob_store: InMemoryArtifactBlobStore,
    outbox_store: InMemoryOutboxStore,
    enqueuer: RecordingJobEnqueuer,
) -> None:
    _seed_medico(operator_store)
    headers = {**_auth_header(client), "Idempotency-Key": "art-idem"}
    patient_id = _create_patient(client, headers)
    files = {"file": ("vitals.csv", VITALS_NORMAL, "text/csv")}

    first = client.post(f"/patients/{patient_id}/cases", headers=headers, files=files)
    second = client.post(f"/patients/{patient_id}/cases", headers=headers, files=files)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert len(blob_store._objects) == 1
    assert len(outbox_store._by_id) == 1
    assert len(enqueuer.jobs) == 1


def test_artifact_storage_error_is_public_type() -> None:
    store = FailingArtifactBlobStore()
    with pytest.raises(ArtifactStorageError):
        store.put(
            bucket="limen",
            object_key="x",
            content=b"a",
            content_type="text/csv",
        )
