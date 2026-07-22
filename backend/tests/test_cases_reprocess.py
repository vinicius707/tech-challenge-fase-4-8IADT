"""TDD T5.3 — POST /cases/{id}/reprocess seletivo + refundição do Risco."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
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
from app.cases import runtime as runtime_mod
from app.cases.processing import process_modality_for_case
from app.cases.service import (
    ArtifactRecord,
    CaseRecord,
    CaseService,
    InMemoryCaseStore,
    ModalityRecord,
    get_case_service,
)
from app.cases.storage import InMemoryArtifactBlobStore
from app.main import app
from app.outbox import completion as completion_mod
from app.outbox.jobs import process_modality
from app.outbox.service import (
    InMemoryOutboxStore,
    OutboxDispatcher,
    RecordingJobEnqueuer,
)
from app.patients.service import InMemoryPatientStore, PatientService, get_patient_service

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_MEDIUM = (
    REPO_ROOT / "data" / "fixtures" / "vitals" / "vitals_medium.csv"
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


@pytest.fixture(autouse=True)
def reset_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    monkeypatch.delenv("LIMEN_FORCE_FAIL_MODALITIES", raising=False)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


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


def _seed_partial_case(
    *,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    monkeypatch: pytest.MonkeyPatch,
) -> uuid.UUID:
    """vitals done (MEDIO) + audio failed — Artefato de vitais permanece no blob store."""
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    object_key = f"cases/{case_id}/vitals/vitals_medium.csv"
    blob_store.put(
        bucket="limen",
        object_key=object_key,
        content=VITALS_MEDIUM,
        content_type="text/csv",
    )
    case_store.save(
        CaseRecord(
            id=case_id,
            patient_id=uuid.uuid4(),
            status="pending",
            risk_score=None,
            risk_level=None,
            idempotency_key=str(uuid.uuid4()),
            content_sha256="x",
            created_at=now,
            updated_at=now,
            modalities=[
                ModalityRecord(
                    id=uuid.uuid4(),
                    case_id=case_id,
                    modality="vitals",
                    status="pending",
                    artifact_id=artifact_id,
                    created_at=now,
                    updated_at=now,
                ),
                ModalityRecord(
                    id=uuid.uuid4(),
                    case_id=case_id,
                    modality="audio",
                    status="pending",
                    artifact_id=None,
                    created_at=now,
                    updated_at=now,
                ),
            ],
            artifacts=[
                ArtifactRecord(
                    id=artifact_id,
                    case_id=case_id,
                    modality="vitals",
                    bucket="limen",
                    object_key=object_key,
                    content_sha256="x",
                    content_type="text/csv",
                    created_at=now,
                )
            ],
        )
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)
    monkeypatch.setenv("LIMEN_FORCE_FAIL_MODALITIES", "audio")
    process_modality_for_case(case_id, "vitals")
    process_modality_for_case(case_id, "audio")
    monkeypatch.delenv("LIMEN_FORCE_FAIL_MODALITIES", raising=False)

    done = case_store.get(case_id)
    assert done is not None
    assert done.status == "done"
    assert done.risk_level == "MEDIO"
    assert {m.modality: m.status for m in done.modalities} == {
        "vitals": "done",
        "audio": "failed",
    }
    # Artefato ainda disponível (não foi reenviado / apagado).
    assert blob_store.get("limen", object_key) == VITALS_MEDIUM
    return case_id


def test_reprocess_requires_auth(
    client: TestClient,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_id = _seed_partial_case(
        case_store=case_store,
        blob_store=blob_store,
        monkeypatch=monkeypatch,
    )
    response = client.post(f"/cases/{case_id}/reprocess")
    assert response.status_code == 401


def test_reprocess_unknown_case_returns_404(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_medico(operator_store)
    response = client.post(
        f"/cases/{uuid.uuid4()}/reprocess",
        headers=_auth_header(client),
    )
    assert response.status_code == 404


def test_reprocess_without_failed_modalities_returns_409(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
) -> None:
    _seed_medico(operator_store)
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    case_store.save(
        CaseRecord(
            id=case_id,
            patient_id=uuid.uuid4(),
            status="done",
            risk_score=0.1,
            risk_level="BAIXO",
            idempotency_key=None,
            content_sha256=None,
            created_at=now,
            updated_at=now,
            modalities=[
                ModalityRecord(
                    id=uuid.uuid4(),
                    case_id=case_id,
                    modality="vitals",
                    status="done",
                    artifact_id=None,
                    created_at=now,
                    updated_at=now,
                )
            ],
        )
    )
    response = client.post(
        f"/cases/{case_id}/reprocess",
        headers=_auth_header(client),
    )
    assert response.status_code == 409


def test_reprocess_enqueues_only_failed_modalities_and_refunds_risk(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    outbox_store: InMemoryOutboxStore,
    enqueuer: RecordingJobEnqueuer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_medico(operator_store)
    case_id = _seed_partial_case(
        case_store=case_store,
        blob_store=blob_store,
        monkeypatch=monkeypatch,
    )
    before_jobs = len(enqueuer.jobs)

    response = client.post(
        f"/cases/{case_id}/reprocess",
        headers=_auth_header(client),
    )
    assert response.status_code == 202
    body = response.json()
    assert body["id"] == str(case_id)
    assert body["status"] == "processing"
    by_mod = {m["modality"]: m["status"] for m in body["modalities"]}
    assert by_mod == {"vitals": "done", "audio": "pending"}

    new_jobs = enqueuer.jobs[before_jobs:]
    assert len(new_jobs) == 1
    assert new_jobs[0]["payload"]["modality"] == "audio"
    assert new_jobs[0]["payload"]["case_id"] == str(case_id)

    # Artefato de vitais intacto (reprocess não reenvia blob).
    case = case_store.get(case_id)
    assert case is not None
    art = case.artifacts[0]
    assert blob_store.get(art.bucket, art.object_key) == VITALS_MEDIUM

    completion_mod.configure_completion_store(outbox_store)
    runtime_mod.configure_case_runtime(case_store, blob_store)
    outbox_job_id = new_jobs[0]["payload"]["outbox_job_id"]
    process_modality(str(case_id), "audio", outbox_job_id=outbox_job_id)

    refunded = case_store.get(case_id)
    assert refunded is not None
    assert refunded.status == "done"
    assert {m.modality: m.status for m in refunded.modalities} == {
        "vitals": "done",
        "audio": "done",
    }
    # vitals MEDIO (0.55) + stub audio BAIXO (0.10) → média 0.325 → BAIXO
    assert refunded.risk_level == "BAIXO"
    assert refunded.risk_score == pytest.approx(0.325)


def test_reprocess_body_filters_failed_modalities(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    enqueuer: RecordingJobEnqueuer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_medico(operator_store)
    case_id = _seed_partial_case(
        case_store=case_store,
        blob_store=blob_store,
        monkeypatch=monkeypatch,
    )
    before = len(enqueuer.jobs)

    response = client.post(
        f"/cases/{case_id}/reprocess",
        headers=_auth_header(client),
        json={"modalities": ["vitals"]},
    )
    # vitals não está failed → nada elegível
    assert response.status_code == 409
    assert len(enqueuer.jobs) == before

    response = client.post(
        f"/cases/{case_id}/reprocess",
        headers=_auth_header(client),
        json={"modalities": ["audio"]},
    )
    assert response.status_code == 202
    new_jobs = enqueuer.jobs[before:]
    assert len(new_jobs) == 1
    assert new_jobs[0]["payload"]["modality"] == "audio"
