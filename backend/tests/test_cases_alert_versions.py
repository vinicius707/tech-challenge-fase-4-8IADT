"""TDD T5.4 — Alerta v2 append-only quando reprocess muda o risk_level."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.cases import runtime as runtime_mod
from app.cases.processing import process_modality_for_case
from app.cases.service import (
    ArtifactRecord,
    CaseRecord,
    CaseService,
    InMemoryCaseStore,
    ModalityRecord,
)
from app.cases.storage import InMemoryArtifactBlobStore
from app.outbox import completion as completion_mod
from app.outbox.service import InMemoryOutboxStore, OutboxDispatcher, RecordingJobEnqueuer
from app.patients.service import InMemoryPatientStore

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_MEDIUM = (
    REPO_ROOT / "data" / "fixtures" / "vitals" / "vitals_medium.csv"
).read_bytes()
AUDIO_SPEECH = (
    REPO_ROOT / "data" / "fixtures" / "audio" / "audio_speech.wav"
).read_bytes()


@pytest.fixture(autouse=True)
def reset_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    monkeypatch.delenv("LIMEN_FORCE_FAIL_MODALITIES", raising=False)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def _seed_partial_medio_with_alert_v1(
    *,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    monkeypatch: pytest.MonkeyPatch,
) -> uuid.UUID:
    """vitals MEDIO (Alerta v1) + audio failed."""
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    vitals_artifact_id = uuid.uuid4()
    audio_artifact_id = uuid.uuid4()
    vitals_key = f"cases/{case_id}/vitals/vitals_medium.csv"
    audio_key = f"cases/{case_id}/audio/audio_speech.wav"
    blob_store.put(
        bucket="limen",
        object_key=vitals_key,
        content=VITALS_MEDIUM,
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
                    artifact_id=vitals_artifact_id,
                    created_at=now,
                    updated_at=now,
                ),
                ModalityRecord(
                    id=uuid.uuid4(),
                    case_id=case_id,
                    modality="audio",
                    status="pending",
                    artifact_id=audio_artifact_id,
                    created_at=now,
                    updated_at=now,
                ),
            ],
            artifacts=[
                ArtifactRecord(
                    id=vitals_artifact_id,
                    case_id=case_id,
                    modality="vitals",
                    bucket="limen",
                    object_key=vitals_key,
                    content_sha256="x",
                    content_type="text/csv",
                    created_at=now,
                ),
                ArtifactRecord(
                    id=audio_artifact_id,
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
    runtime_mod.configure_case_runtime(case_store, blob_store)
    monkeypatch.setenv("LIMEN_FORCE_FAIL_MODALITIES", "audio")
    process_modality_for_case(case_id, "vitals")
    process_modality_for_case(case_id, "audio")
    monkeypatch.delenv("LIMEN_FORCE_FAIL_MODALITIES", raising=False)

    done = case_store.get(case_id)
    assert done is not None
    assert done.risk_level == "MEDIO"
    assert len(done.alerts) == 1
    assert done.alerts[0].version == 1
    assert done.alerts[0].level == "MEDIO"
    return case_id


def test_reprocess_level_change_appends_alert_v2_keeping_v1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cenário 3: Alerta v1 permanece; nova versão quando risk_level muda."""
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_partial_medio_with_alert_v1(
        case_store=case_store,
        blob_store=blob_store,
        monkeypatch=monkeypatch,
    )
    v1 = case_store.get(case_id).alerts[0]

    # Reprocess: audio pending → done (stub BAIXO) → fusão BAIXO
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
        )
    )

    process_modality_for_case(case_id, "audio")

    refunded = case_store.get(case_id)
    assert refunded is not None
    assert refunded.risk_level == "BAIXO"
    assert len(refunded.alerts) == 2

    by_version = {a.version: a for a in refunded.alerts}
    assert by_version[1].id == v1.id
    assert by_version[1].level == "MEDIO"
    assert by_version[2].level == "BAIXO"
    assert by_version[2].case_id == case_id


def test_get_case_exposes_all_alert_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_partial_medio_with_alert_v1(
        case_store=case_store,
        blob_store=blob_store,
        monkeypatch=monkeypatch,
    )
    case = case_store.get(case_id)
    assert case is not None
    now = datetime.now(tz=UTC)
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
        )
    )
    process_modality_for_case(case_id, "audio")

    service = CaseService(
        store=case_store,
        patient_store=InMemoryPatientStore(),
        blob_store=blob_store,
        outbox_dispatcher=OutboxDispatcher(
            store=InMemoryOutboxStore(),
            enqueuer=RecordingJobEnqueuer(),
        ),
    )
    response = service.get(case_id)

    assert response.risk_level == "BAIXO"
    assert len(response.alerts) == 2
    versions = sorted(a.version for a in response.alerts)
    assert versions == [1, 2]
    levels = {a.version: a.level for a in response.alerts}
    assert levels == {1: "MEDIO", 2: "BAIXO"}


def test_unchanged_risk_level_does_not_append_alert_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_partial_medio_with_alert_v1(
        case_store=case_store,
        blob_store=blob_store,
        monkeypatch=monkeypatch,
    )
    # Reprocess audio mas força falha de novo → nível continua MEDIO
    case = case_store.get(case_id)
    assert case is not None
    now = datetime.now(tz=UTC)
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
        )
    )
    monkeypatch.setenv("LIMEN_FORCE_FAIL_MODALITIES", "audio")
    process_modality_for_case(case_id, "audio")

    done = case_store.get(case_id)
    assert done is not None
    assert done.risk_level == "MEDIO"
    assert len(done.alerts) == 1
    assert done.alerts[0].version == 1
