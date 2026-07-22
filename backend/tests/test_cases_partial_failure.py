"""TDD T5.2 — falha parcial: modalidade failed + Caso done com fusão só de done."""

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
from app.cases.vitals_engine import (
    ModalityRisk,
    fuse_done_modalities,
    risk_level_from_score,
)
from app.outbox import completion as completion_mod
from app.outbox.jobs import process_modality
from app.outbox.service import InMemoryOutboxStore, OutboxDispatcher, RecordingJobEnqueuer

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"


@pytest.fixture(autouse=True)
def reset_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    monkeypatch.delenv("LIMEN_FORCE_FAIL_MODALITIES", raising=False)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def test_fusion_renormalizes_weights_over_done_modalities_only() -> None:
    vitals = ModalityRisk(score=0.55, level="MEDIO", anomalies=())
    audio = ModalityRisk(score=0.85, level="ALTO", anomalies=())

    both = fuse_done_modalities([vitals, audio])
    assert both.score == pytest.approx(0.70)
    assert both.level == risk_level_from_score(both.score)

    only_vitals = fuse_done_modalities([vitals])
    assert only_vitals.score == pytest.approx(0.55)
    assert only_vitals.level == "MEDIO"


def _seed_case_vitals_and_audio_stub(
    *,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    fixture_name: str = "vitals_medium.csv",
) -> uuid.UUID:
    content = (VITALS_DIR / fixture_name).read_bytes()
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    vitals_artifact_id = uuid.uuid4()
    object_key = f"cases/{case_id}/vitals/{fixture_name}"
    blob_store.put(
        bucket="limen",
        object_key=object_key,
        content=content,
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
                    artifact_id=vitals_artifact_id,
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
                    id=vitals_artifact_id,
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
    return case_id


def test_forced_stub_failure_leaves_case_done_with_vitals_risk_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cenário 1: vitals done + audio failed → Caso done; risco só de vitals."""
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    outbox_store = InMemoryOutboxStore()
    case_id = _seed_case_vitals_and_audio_stub(
        case_store=case_store,
        blob_store=blob_store,
        fixture_name="vitals_medium.csv",
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
    mid = case_store.get(case_id)
    assert mid is not None
    assert next(m.status for m in mid.modalities if m.modality == "vitals") == "done"
    assert next(m.status for m in mid.modalities if m.modality == "audio") == "pending"
    # Ainda há modalidade não terminal → Caso não fecha.
    assert mid.status == "processing"

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


def test_process_modality_for_case_marks_forced_failure_without_closing_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_case_vitals_and_audio_stub(
        case_store=case_store,
        blob_store=blob_store,
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)
    monkeypatch.setenv("LIMEN_FORCE_FAIL_MODALITIES", "audio")

    process_modality_for_case(case_id, "audio")

    case = case_store.get(case_id)
    assert case is not None
    assert next(m.status for m in case.modalities if m.modality == "audio") == "failed"
    assert next(m.status for m in case.modalities if m.modality == "vitals") == "pending"
    assert case.status == "processing"
    assert case.risk_level is None
