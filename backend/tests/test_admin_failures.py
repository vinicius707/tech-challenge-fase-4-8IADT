"""TDD T5.7 — Falhas de Processamento (DLQ): list/redrive/discard + audit + 403."""

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
from app.failures.service import (
    InMemoryFailureStore,
    get_failure_service,
)
from app.main import app
from app.outbox import completion as completion_mod
from app.outbox.service import (
    InMemoryOutboxStore,
    OutboxDispatcher,
    RecordingJobEnqueuer,
)
from app.patients.audit import DLQ_DISCARD, DLQ_REDRIVE, InMemoryAuditStore
from app.patients.service import (
    InMemoryPatientStore,
    PatientRecord,
    PatientService,
    get_patient_service,
)

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
    return RecordingJobEnqueuer()


@pytest.fixture
def failure_store() -> InMemoryFailureStore:
    return InMemoryFailureStore()


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
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    outbox_store: InMemoryOutboxStore,
    enqueuer: RecordingJobEnqueuer,
    failure_store: InMemoryFailureStore,
    audit_store: InMemoryAuditStore,
    blacklist_store: InMemoryBlacklistStore,
) -> TestClient:
    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
    patient_service = PatientService(
        store=patient_store,
        case_store=case_store,
        audit_store=audit_store,
    )
    dispatcher = OutboxDispatcher(store=outbox_store, enqueuer=enqueuer)
    case_service = CaseService(
        store=case_store,
        patient_store=patient_store,
        blob_store=blob_store,
        outbox_dispatcher=dispatcher,
    )
    from app.failures.service import FailureService

    failure_service = FailureService(
        store=failure_store,
        case_store=case_store,
        outbox_dispatcher=dispatcher,
        audit_store=audit_store,
    )
    from app.failures.service import configure_failure_recorder

    configure_failure_recorder(failure_service)
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_blacklist_store] = lambda: blacklist_store
    app.dependency_overrides[get_patient_service] = lambda: patient_service
    app.dependency_overrides[get_case_service] = lambda: case_service
    app.dependency_overrides[get_failure_service] = lambda: failure_service
    with TestClient(app) as test_client:
        yield test_client
    configure_failure_recorder(None)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.failures.service import configure_failure_recorder

    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    configure_failure_recorder(None)
    for key in (
        "LIMEN_FORCE_FAIL_MODALITIES",
        "LIMEN_FORCE_PERMANENT_FAIL_MODALITIES",
    ):
        monkeypatch.delenv(key, raising=False)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    configure_failure_recorder(None)


def _seed_operator(
    store: InMemoryOperatorStore, *, username: str, password: str, role: str
) -> OperatorRecord:
    operator = OperatorRecord(
        id=uuid.uuid4(),
        username=username,
        password_hash=hash_password(password),
        role=role,
    )
    store.save(operator)
    return operator


def _auth_header(client: TestClient, *, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seed_case_with_forced_audio_failure(
    *,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    patient_store: InMemoryPatientStore,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[uuid.UUID, uuid.UUID]:
    """vitals ok + audio falha permanente → DLQ."""
    now = datetime.now(tz=UTC)
    patient_id = uuid.uuid4()
    patient_store.save(
        PatientRecord(
            id=patient_id,
            code="PAC-DLQ-1",
            sensitive_label_ciphertext=None,
            created_at=now,
            updated_at=now,
        )
    )
    case_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    object_key = f"cases/{case_id}/vitals/vitals_normal.csv"
    blob_store.put(
        bucket="limen",
        object_key=object_key,
        content=VITALS_NORMAL,
        content_type="text/csv",
    )
    case_store.save(
        CaseRecord(
            id=case_id,
            patient_id=patient_id,
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
    monkeypatch.setenv("LIMEN_FORCE_PERMANENT_FAIL_MODALITIES", "audio")
    process_modality_for_case(case_id, "vitals")
    process_modality_for_case(case_id, "audio")
    return case_id, patient_id


def test_medico_forbidden_on_admin_failures(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_operator(
        operator_store, username="medico", password="medico-secret", role="medico"
    )
    headers = _auth_header(client, username="medico", password="medico-secret")

    assert client.get("/admin/failures", headers=headers).status_code == 403
    fake_id = uuid.uuid4()
    assert client.get(f"/admin/failures/{fake_id}", headers=headers).status_code == 403
    assert (
        client.post(f"/admin/failures/{fake_id}/redrive", headers=headers).status_code
        == 403
    )
    assert (
        client.post(f"/admin/failures/{fake_id}/discard", headers=headers).status_code
        == 403
    )


def test_forced_failure_appears_in_dlq_and_redrive_reenqueues(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    patient_store: InMemoryPatientStore,
    outbox_store: InMemoryOutboxStore,
    enqueuer: RecordingJobEnqueuer,
    audit_store: InMemoryAuditStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _seed_operator(
        operator_store, username="admin", password="admin-secret", role="admin"
    )
    headers = _auth_header(client, username="admin", password="admin-secret")
    case_id, patient_id = _seed_case_with_forced_audio_failure(
        case_store=case_store,
        blob_store=blob_store,
        patient_store=patient_store,
        monkeypatch=monkeypatch,
    )

    listed = client.get("/admin/failures", headers=headers)
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    failure = items[0]
    assert failure["case_id"] == str(case_id)
    assert failure["modality"] == "audio"
    assert failure["status"] == "open"
    assert failure["error_summary"]
    assert failure["attempts"] >= 1

    detail = client.get(f"/admin/failures/{failure['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == failure["id"]
    assert detail.json()["modality"] == "audio"

    enqueuer.jobs.clear()
    redrive = client.post(
        f"/admin/failures/{failure['id']}/redrive",
        headers=headers,
    )
    assert redrive.status_code == 200
    body = redrive.json()
    assert body["status"] == "redriven"

    case = case_store.get(case_id)
    assert case is not None
    assert next(m.status for m in case.modalities if m.modality == "audio") == "pending"
    assert any(
        j["payload"].get("modality") == "audio"
        and j["payload"].get("case_id") == str(case_id)
        for j in enqueuer.jobs
    )
    audits = [r for r in audit_store.list_by_patient(patient_id) if r.action == DLQ_REDRIVE]
    assert len(audits) == 1
    assert audits[0].operator_id == admin.id


def test_discard_marks_failure_and_audits(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    patient_store: InMemoryPatientStore,
    enqueuer: RecordingJobEnqueuer,
    audit_store: InMemoryAuditStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = _seed_operator(
        operator_store, username="admin", password="admin-secret", role="admin"
    )
    headers = _auth_header(client, username="admin", password="admin-secret")
    case_id, patient_id = _seed_case_with_forced_audio_failure(
        case_store=case_store,
        blob_store=blob_store,
        patient_store=patient_store,
        monkeypatch=monkeypatch,
    )

    failure_id = client.get("/admin/failures", headers=headers).json()["items"][0]["id"]
    enqueuer.jobs.clear()

    discarded = client.post(
        f"/admin/failures/{failure_id}/discard",
        headers=headers,
    )
    assert discarded.status_code == 200
    assert discarded.json()["status"] == "discarded"

    # Não reenfileira; modalidade permanece failed.
    assert enqueuer.jobs == []
    case = case_store.get(case_id)
    assert case is not None
    assert next(m.status for m in case.modalities if m.modality == "audio") == "failed"

    open_list = client.get("/admin/failures", headers=headers)
    assert open_list.json()["items"] == []

    audits = [
        r for r in audit_store.list_by_patient(patient_id) if r.action == DLQ_DISCARD
    ]
    assert len(audits) == 1
    assert audits[0].operator_id == admin.id


def test_get_unknown_failure_returns_404(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
) -> None:
    _seed_operator(
        operator_store, username="admin", password="admin-secret", role="admin"
    )
    headers = _auth_header(client, username="admin", password="admin-secret")
    response = client.get(f"/admin/failures/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404
