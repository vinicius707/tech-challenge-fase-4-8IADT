"""TDD T7.2 — SSE de Alertas via fetch + Bearer (ADR 0022)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.alerts.hub import get_alert_hub, publish_alert_event, reset_alert_hub
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
from app.outbox.service import InMemoryOutboxStore, OutboxDispatcher, RecordingJobEnqueuer
from app.patients.service import InMemoryPatientStore, PatientService, get_patient_service

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_MEDIUM = (
    REPO_ROOT / "data" / "fixtures" / "vitals" / "vitals_medium.csv"
).read_bytes()
AUDIO_SPEECH = (
    REPO_ROOT / "data" / "fixtures" / "audio" / "audio_speech.wav"
).read_bytes()


@pytest.fixture(autouse=True)
def reset_hub_and_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_alert_hub()
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    monkeypatch.delenv("LIMEN_FORCE_FAIL_MODALITIES", raising=False)
    monkeypatch.setenv("LIMEN_SSE_HEARTBEAT_SECONDS", "0.2")
    yield
    reset_alert_hub()
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.setenv("JWT_ACCESS_TTL_SECONDS", "900")


@pytest.fixture
def client(auth_env: None) -> TestClient:
    operator_store = InMemoryOperatorStore()
    blacklist_store = InMemoryBlacklistStore()
    patient_store = InMemoryPatientStore()
    case_store = InMemoryCaseStore()
    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
    operator_store.save(
        OperatorRecord(
            id=uuid.uuid4(),
            username="medico_sse",
            password_hash=hash_password("senha-ok-12"),
            role="medico",
        )
    )
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


def _seed_partial_medio(
    *,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    monkeypatch: pytest.MonkeyPatch,
) -> uuid.UUID:
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    vitals_id = uuid.uuid4()
    audio_id = uuid.uuid4()
    vitals_key = f"cases/{case_id}/vitals/vitals_medium.csv"
    audio_key = f"cases/{case_id}/audio/audio_speech.wav"
    blob_store.put(
        bucket="limen", object_key=vitals_key, content=VITALS_MEDIUM, content_type="text/csv"
    )
    blob_store.put(
        bucket="limen", object_key=audio_key, content=AUDIO_SPEECH, content_type="audio/wav"
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
                    artifact_id=vitals_id,
                    created_at=now,
                    updated_at=now,
                ),
                ModalityRecord(
                    id=uuid.uuid4(),
                    case_id=case_id,
                    modality="audio",
                    status="pending",
                    artifact_id=audio_id,
                    created_at=now,
                    updated_at=now,
                ),
            ],
            artifacts=[
                ArtifactRecord(
                    id=vitals_id,
                    case_id=case_id,
                    modality="vitals",
                    bucket="limen",
                    object_key=vitals_key,
                    content_sha256="x",
                    content_type="text/csv",
                    created_at=now,
                ),
                ArtifactRecord(
                    id=audio_id,
                    case_id=case_id,
                    modality="audio",
                    bucket="limen",
                    object_key=audio_key,
                    content_sha256="y",
                    content_type="audio/wav",
                    created_at=now,
                ),
            ],
        )
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)
    completion_mod.configure_completion_store(case_store)
    monkeypatch.setenv("LIMEN_FORCE_FAIL_MODALITIES", "audio")
    process_modality_for_case(case_id, "vitals")
    process_modality_for_case(case_id, "audio")
    monkeypatch.delenv("LIMEN_FORCE_FAIL_MODALITIES", raising=False)
    return case_id


def test_alerts_stream_requires_bearer(client: TestClient) -> None:
    response = client.get("/alerts/stream")
    assert response.status_code == 401


def test_alerts_stream_response_is_event_stream() -> None:
    from app.alerts.router import alerts_stream
    from app.auth.deps import AccessTokenClaims

    claims = AccessTokenClaims(
        sub=uuid.uuid4(),
        username="medico_sse",
        role="medico",
        jti="jti-test",
        exp=datetime.now(tz=UTC),
        raw={},
    )
    response = alerts_stream(_claims=claims)
    assert response.media_type == "text/event-stream"
    assert response.headers.get("cache-control") == "no-cache"
    assert response.headers.get("connection") == "keep-alive"


def test_publish_alert_event_delivers_to_subscriber() -> None:
    hub = get_alert_hub()
    q = hub.subscribe()
    try:
        publish_alert_event(
            "alert.created",
            {
                "alert_id": str(uuid.uuid4()),
                "case_id": str(uuid.uuid4()),
                "level": "MEDIO",
                "version": 1,
                "created_at": datetime.now(tz=UTC).isoformat(),
            },
        )
        msg = q.get(timeout=1.0)
        assert msg["event"] == "alert.created"
        assert msg["data"]["level"] == "MEDIO"
        assert msg["data"]["version"] == 1
    finally:
        hub.unsubscribe(q)


def test_fusion_publishes_alert_created(monkeypatch: pytest.MonkeyPatch) -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    hub = get_alert_hub()
    q = hub.subscribe()
    try:
        case_id = _seed_partial_medio(
            case_store=case_store, blob_store=blob_store, monkeypatch=monkeypatch
        )
        msg = q.get(timeout=2.0)
        assert msg["event"] == "alert.created"
        assert msg["data"]["case_id"] == str(case_id)
        assert msg["data"]["version"] == 1
        assert msg["data"]["level"] == "MEDIO"
        assert "alert_id" in msg["data"]
        assert "created_at" in msg["data"]
    finally:
        hub.unsubscribe(q)


def test_reprocess_level_change_publishes_alert_updated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    hub = get_alert_hub()
    q = hub.subscribe()
    try:
        case_id = _seed_partial_medio(
            case_store=case_store, blob_store=blob_store, monkeypatch=monkeypatch
        )
        assert q.get(timeout=2.0)["event"] == "alert.created"

        now = datetime.now(tz=UTC)
        case = case_store.get(case_id)
        assert case is not None
        case_store.save(
            CaseRecord(
                id=case.id,
                patient_id=case.patient_id,
                status="processing",
                risk_score=case.risk_score,
                risk_level=case.risk_level,
                idempotency_key=case.idempotency_key,
                content_sha256=case.content_sha256,
                created_at=case.created_at,
                updated_at=now,
                modalities=[
                    ModalityRecord(
                        id=m.id,
                        case_id=m.case_id,
                        modality=m.modality,
                        status="pending" if m.modality == "audio" else m.status,
                        artifact_id=m.artifact_id,
                        created_at=m.created_at,
                        updated_at=now if m.modality == "audio" else m.updated_at,
                    )
                    for m in case.modalities
                ],
                artifacts=case.artifacts,
                alerts=case.alerts,
                justification=case.justification,
            )
        )
        process_modality_for_case(case_id, "audio")

        msg = q.get(timeout=2.0)
        assert msg["event"] == "alert.updated"
        assert msg["data"]["case_id"] == str(case_id)
        assert msg["data"]["version"] == 2
    finally:
        hub.unsubscribe(q)
