"""TDD T3.8 — AnomalyEngine + Fusion → Risco (sem Alerta)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.cases import runtime as runtime_mod
from app.cases.processing import process_vitals_for_case
from app.cases.service import (
    ArtifactRecord,
    CaseRecord,
    InMemoryCaseStore,
    ModalityRecord,
)
from app.cases.storage import InMemoryArtifactBlobStore
from app.cases.vitals_engine import VitalsAnomalyEngine, fuse_vitals_only, risk_level_from_score
from app.outbox import completion as completion_mod
from app.outbox.jobs import process_modality
from app.outbox.service import InMemoryOutboxStore, OutboxDispatcher, RecordingJobEnqueuer

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"


@pytest.fixture(autouse=True)
def reset_runtime() -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


@pytest.mark.parametrize(
    ("fixture_name", "expected_level"),
    [
        ("vitals_normal.csv", "BAIXO"),
        ("vitals_medium.csv", "MEDIO"),
        ("vitals_high.csv", "ALTO"),
    ],
)
def test_anomaly_engine_maps_fixtures_to_risk_levels(
    fixture_name: str,
    expected_level: str,
) -> None:
    content = (VITALS_DIR / fixture_name).read_bytes()
    result = VitalsAnomalyEngine().analyze_csv(content)
    fused = fuse_vitals_only(result)

    assert fused.level == expected_level
    assert risk_level_from_score(fused.score) == expected_level
    if expected_level == "BAIXO":
        assert fused.score < 0.40
        assert fused.anomalies == ()
    elif expected_level == "MEDIO":
        assert 0.40 <= fused.score < 0.70
        assert fused.anomalies
    else:
        assert fused.score >= 0.70
        assert fused.anomalies


def _seed_case_with_fixture(
    *,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    fixture_name: str,
) -> uuid.UUID:
    content = (VITALS_DIR / fixture_name).read_bytes()
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
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
                    artifact_id=artifact_id,
                    created_at=now,
                    updated_at=now,
                )
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
    return case_id


@pytest.mark.parametrize(
    ("fixture_name", "expected_level"),
    [
        ("vitals_normal.csv", "BAIXO"),
        ("vitals_medium.csv", "MEDIO"),
        ("vitals_high.csv", "ALTO"),
    ],
)
def test_worker_sets_case_risk_and_done(
    fixture_name: str,
    expected_level: str,
) -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    outbox_store = InMemoryOutboxStore()
    case_id = _seed_case_with_fixture(
        case_store=case_store,
        blob_store=blob_store,
        fixture_name=fixture_name,
    )
    dispatcher = OutboxDispatcher(store=outbox_store, enqueuer=RecordingJobEnqueuer())
    job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "vitals"},
    )
    dispatcher.try_enqueue(job.id)

    runtime_mod.configure_case_runtime(case_store, blob_store)
    completion_mod.configure_completion_store(outbox_store)

    process_modality(str(case_id), "vitals", outbox_job_id=str(job.id))

    done = case_store.get(case_id)
    assert done is not None
    assert done.status == "done"
    assert done.risk_level == expected_level
    assert done.risk_score is not None
    assert done.modalities[0].status == "done"
    assert outbox_store.get(job.id).status == "processed"


def test_worker_reprocess_is_idempotent_for_risk() -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_case_with_fixture(
        case_store=case_store,
        blob_store=blob_store,
        fixture_name="vitals_medium.csv",
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)

    first = process_vitals_for_case(case_id)
    second = process_vitals_for_case(case_id)

    assert first is not None and second is not None
    assert first.risk_score == second.risk_score
    assert first.risk_level == second.risk_level == "MEDIO"
    assert first.status == second.status == "done"
