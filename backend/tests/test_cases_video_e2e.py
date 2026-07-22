"""TDD T6.5 — worker real de vídeo + fusão de Risco (E2E / Cenário 3)."""

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
    InMemoryCaseStore,
    ModalityRecord,
)
from app.cases.storage import InMemoryArtifactBlobStore
from app.outbox import completion as completion_mod
from app.outbox.jobs import process_modality
from app.outbox.rq_client import VIDEO_QUEUE_NAME, resolve_queue
from app.outbox.service import (
    InMemoryOutboxStore,
    OutboxDispatcher,
    RecordingJobEnqueuer,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"
VIDEO_PHYSIO = (
    REPO_ROOT / "data" / "fixtures" / "video" / "video_physio.avi"
).read_bytes()


@pytest.fixture(autouse=True)
def reset_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    monkeypatch.delenv("LIMEN_FORCE_FAIL_MODALITIES", raising=False)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def _seed_vitals_and_video(
    *,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    vitals_fixture: str = "vitals_medium.csv",
    video_filename: str = "video_physio.avi",
    video_bytes: bytes = VIDEO_PHYSIO,
) -> uuid.UUID:
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    vitals_id = uuid.uuid4()
    video_id = uuid.uuid4()
    vitals_key = f"cases/{case_id}/vitals/{vitals_fixture}"
    video_key = f"cases/{case_id}/video/{video_filename}"
    blob_store.put(
        bucket="limen",
        object_key=vitals_key,
        content=(VITALS_DIR / vitals_fixture).read_bytes(),
        content_type="text/csv",
    )
    blob_store.put(
        bucket="limen",
        object_key=video_key,
        content=video_bytes,
        content_type="video/x-msvideo",
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
                    modality="video",
                    status="pending",
                    artifact_id=video_id,
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
                    id=video_id,
                    case_id=case_id,
                    modality="video",
                    bucket="limen",
                    object_key=video_key,
                    content_sha256="x",
                    content_type="video/x-msvideo",
                    created_at=now,
                ),
            ],
        )
    )
    return case_id


def test_video_job_routes_to_video_queue_not_default() -> None:
    assert (
        resolve_queue(
            job_type="process_modality",
            payload={"case_id": str(uuid.uuid4()), "modality": "video"},
        )
        == VIDEO_QUEUE_NAME
    )
    assert (
        resolve_queue(
            job_type="process_modality",
            payload={"case_id": str(uuid.uuid4()), "modality": "vitals"},
        )
        != VIDEO_QUEUE_NAME
    )


def test_worker_process_modality_video_marks_done_with_frames() -> None:
    """Cenário 1 via entrypoint RQ: process_modality (fila video)."""
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    outbox_store = InMemoryOutboxStore()
    case_id = _seed_vitals_and_video(
        case_store=case_store,
        blob_store=blob_store,
    )
    # Só vídeo nesta execução — vitais ficam pending para não fechar ainda.
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
            modalities=[m for m in case.modalities if m.modality == "video"],
            artifacts=[a for a in case.artifacts if a.modality == "video"],
        )
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)
    completion_mod.configure_completion_store(outbox_store)

    enqueuer = RecordingJobEnqueuer()
    dispatcher = OutboxDispatcher(store=outbox_store, enqueuer=enqueuer)
    job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "video"},
    )
    dispatcher.try_enqueue(job.id)
    assert enqueuer.jobs[0]["queue"] == VIDEO_QUEUE_NAME

    process_modality(str(case_id), "video", outbox_job_id=str(job.id))

    done = case_store.get(case_id)
    assert done is not None
    assert next(m.status for m in done.modalities if m.modality == "video") == "done"
    assert any(a.modality == "video_frame" for a in done.artifacts)
    assert done.status == "done"
    assert done.risk_level is not None
    assert outbox_store.get(job.id).status == "processed"


def test_fusion_vitals_and_video_done_considers_both() -> None:
    """Cenário 3: vitals + video done → Risco fundido (não só vitais)."""
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_vitals_and_video(
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

    process_modality_for_case(case_id, "video")
    done = case_store.get(case_id)
    assert done is not None
    by_mod = {m.modality: m.status for m in done.modalities}
    assert by_mod == {"vitals": "done", "video": "done"}
    assert done.status == "done"
    # vitals MEDIO 0.55 + pose ~0.42 → média ~0.485 MEDIO; anomalias de ambas.
    assert done.risk_score == pytest.approx(0.485)
    assert done.risk_level == "MEDIO"
    assert any(a.modality == "video_frame" for a in done.artifacts)


def test_partial_failure_video_failed_vitals_done_closes_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cenário 3: video failed + vitals done → Caso done (falha parcial)."""
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    outbox_store = InMemoryOutboxStore()
    case_id = _seed_vitals_and_video(
        case_store=case_store,
        blob_store=blob_store,
        vitals_fixture="vitals_medium.csv",
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)
    completion_mod.configure_completion_store(outbox_store)
    monkeypatch.setenv("LIMEN_FORCE_FAIL_MODALITIES", "video")

    dispatcher = OutboxDispatcher(store=outbox_store, enqueuer=RecordingJobEnqueuer())
    vitals_job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "vitals"},
    )
    video_job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "video"},
    )
    dispatcher.try_enqueue(vitals_job.id)
    dispatcher.try_enqueue(video_job.id)

    process_modality(str(case_id), "vitals", outbox_job_id=str(vitals_job.id))
    process_modality(str(case_id), "video", outbox_job_id=str(video_job.id))

    done = case_store.get(case_id)
    assert done is not None
    by_mod = {m.modality: m.status for m in done.modalities}
    assert by_mod == {"vitals": "done", "video": "failed"}
    assert done.status == "done"
    assert done.risk_level == "MEDIO"
    assert done.risk_score is not None
    assert 0.40 <= done.risk_score < 0.70
    assert not any(a.modality == "video_frame" for a in done.artifacts)
    assert outbox_store.get(vitals_job.id).status == "processed"
    assert outbox_store.get(video_job.id).status == "processed"
