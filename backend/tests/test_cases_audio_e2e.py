"""TDD T6.11 — badge provider no GET + fusão de Risco / falha parcial (E6.2)."""

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
from app.azure.provider import clear_audio_analysis_cache
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
from app.outbox.rq_client import DEFAULT_QUEUE_NAME, VIDEO_QUEUE_NAME, resolve_queue
from app.outbox.service import (
    InMemoryOutboxStore,
    OutboxDispatcher,
    RecordingJobEnqueuer,
)
from app.patients.service import InMemoryPatientStore, PatientService, get_patient_service

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"
AUDIO_SPEECH = (
    REPO_ROOT / "data" / "fixtures" / "audio" / "audio_speech.wav"
).read_bytes()


@pytest.fixture(autouse=True)
def reset_runtime_and_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    clear_audio_analysis_cache()
    monkeypatch.delenv("LIMEN_FORCE_FAIL_MODALITIES", raising=False)
    monkeypatch.setenv("AZURE_ENABLED", "false")
    yield
    clear_audio_analysis_cache()
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def _seed_vitals_and_audio(
    *,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    vitals_fixture: str = "vitals_medium.csv",
) -> uuid.UUID:
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    vitals_id = uuid.uuid4()
    audio_id = uuid.uuid4()
    vitals_key = f"cases/{case_id}/vitals/{vitals_fixture}"
    audio_key = f"cases/{case_id}/audio/audio_speech.wav"
    blob_store.put(
        bucket="limen",
        object_key=vitals_key,
        content=(VITALS_DIR / vitals_fixture).read_bytes(),
        content_type="text/csv",
    )
    blob_store.put(
        bucket="limen",
        object_key=audio_key,
        content=AUDIO_SPEECH,
        content_type="audio/wav",
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
                    content_sha256="x",
                    content_type="audio/wav",
                    created_at=now,
                ),
            ],
        )
    )
    return case_id


def test_audio_job_routes_to_default_queue_not_video() -> None:
    assert (
        resolve_queue(
            job_type="process_modality",
            payload={"case_id": str(uuid.uuid4()), "modality": "audio"},
        )
        == DEFAULT_QUEUE_NAME
    )
    assert (
        resolve_queue(
            job_type="process_modality",
            payload={"case_id": str(uuid.uuid4()), "modality": "audio"},
        )
        != VIDEO_QUEUE_NAME
    )


def test_fusion_vitals_and_audio_done_considers_both() -> None:
    """Cenário 6: vitals + audio done → Risco fundido (não só vitais)."""
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_vitals_and_audio(
        case_store=case_store,
        blob_store=blob_store,
        vitals_fixture="vitals_medium.csv",
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)

    process_modality_for_case(case_id, "vitals")
    mid = case_store.get(case_id)
    assert mid is not None
    assert mid.status == "processing"
    assert mid.risk_level is None

    process_modality_for_case(case_id, "audio")
    done = case_store.get(case_id)
    assert done is not None
    by_mod = {m.modality: m.status for m in done.modalities}
    assert by_mod == {"vitals": "done", "audio": "done"}
    assert done.status == "done"
    # vitals MEDIO 0.55 + audio local ~0.1601 → média ~0.355 BAIXO
    # (se só vitais: MEDIO 0.55 — prova que a fusão considera o áudio).
    assert done.risk_score == pytest.approx(0.35505)
    assert done.risk_level == "BAIXO"
    audio_mod = next(m for m in done.modalities if m.modality == "audio")
    assert audio_mod.provider == "local"


def test_partial_failure_audio_failed_vitals_done_closes_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cenário 6: audio failed + vitals done → Caso done (falha parcial)."""
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    outbox_store = InMemoryOutboxStore()
    case_id = _seed_vitals_and_audio(
        case_store=case_store,
        blob_store=blob_store,
        vitals_fixture="vitals_medium.csv",
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)
    completion_mod.configure_completion_store(outbox_store)
    monkeypatch.setenv("LIMEN_FORCE_FAIL_MODALITIES", "audio")

    dispatcher = OutboxDispatcher(store=outbox_store, enqueuer=RecordingJobEnqueuer())
    vitals_job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "vitals"},
    )
    audio_job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "audio"},
    )
    dispatcher.try_enqueue(vitals_job.id)
    dispatcher.try_enqueue(audio_job.id)

    process_modality(str(case_id), "vitals", outbox_job_id=str(vitals_job.id))
    process_modality(str(case_id), "audio", outbox_job_id=str(audio_job.id))

    done = case_store.get(case_id)
    assert done is not None
    by_mod = {m.modality: m.status for m in done.modalities}
    assert by_mod == {"vitals": "done", "audio": "failed"}
    assert done.status == "done"
    assert done.risk_level == "MEDIO"
    assert done.risk_score is not None
    assert 0.40 <= done.risk_score < 0.70
    assert outbox_store.get(vitals_job.id).status == "processed"
    assert outbox_store.get(audio_job.id).status == "processed"


def test_get_case_exposes_audio_provider_badge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /cases/{id} expõe provider azure|local|cache na modalidade audio."""
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.setenv("JWT_ACCESS_TTL_SECONDS", "900")

    operator_store = InMemoryOperatorStore()
    operator_store.save(
        OperatorRecord(
            id=uuid.uuid4(),
            username="medico",
            password_hash=hash_password("medico-secret"),
            role="medico",
        )
    )
    patient_store = InMemoryPatientStore()
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    blacklist_store = InMemoryBlacklistStore()
    outbox_store = InMemoryOutboxStore()
    case_id = _seed_vitals_and_audio(
        case_store=case_store,
        blob_store=blob_store,
    )
    # Só áudio nesta execução — fecha o Caso com provider.
    case = case_store.get(case_id)
    assert case is not None
    case_store.save(
        CaseRecord(
            id=case.id,
            patient_id=case.patient_id,
            status=case.status,
            risk_score=None,
            risk_level=None,
            idempotency_key=case.idempotency_key,
            content_sha256=case.content_sha256,
            created_at=case.created_at,
            updated_at=case.updated_at,
            modalities=[m for m in case.modalities if m.modality == "audio"],
            artifacts=[a for a in case.artifacts if a.modality == "audio"],
        )
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)

    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
    patient_service = PatientService(store=patient_store, case_store=case_store)
    case_service = CaseService(
        store=case_store,
        patient_store=patient_store,
        blob_store=blob_store,
        outbox_dispatcher=OutboxDispatcher(
            store=outbox_store, enqueuer=RecordingJobEnqueuer()
        ),
    )
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_blacklist_store] = lambda: blacklist_store
    app.dependency_overrides[get_patient_service] = lambda: patient_service
    app.dependency_overrides[get_case_service] = lambda: case_service

    try:
        process_modality_for_case(case_id, "audio")
        with TestClient(app) as client:
            login = client.post(
                "/auth/login",
                json={"username": "medico", "password": "medico-secret"},
            )
            assert login.status_code == 200
            headers = {
                "Authorization": f"Bearer {login.json()['access_token']}"
            }
            response = client.get(f"/cases/{case_id}", headers=headers)
        assert response.status_code == 200
        body = response.json()
        audio = next(m for m in body["modalities"] if m["modality"] == "audio")
        assert audio["status"] == "done"
        assert audio["provider"] == "local"
        assert body["status"] == "done"
        assert body["risk_level"] is not None
    finally:
        app.dependency_overrides.clear()
