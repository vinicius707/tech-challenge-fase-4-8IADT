"""TDD T3.9 — Alerta v1 persistido quando Risco ≥ MEDIO (sem SSE)."""

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
    CaseService,
    InMemoryCaseStore,
    ModalityRecord,
)
from app.cases.storage import InMemoryArtifactBlobStore
from app.outbox import completion as completion_mod
from app.outbox.jobs import process_modality
from app.outbox.service import InMemoryOutboxStore, OutboxDispatcher, RecordingJobEnqueuer
from app.patients.service import InMemoryPatientStore

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"


@pytest.fixture(autouse=True)
def reset_runtime() -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


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


def test_baixo_does_not_create_alert() -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_case_with_fixture(
        case_store=case_store,
        blob_store=blob_store,
        fixture_name="vitals_normal.csv",
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)

    done = process_vitals_for_case(case_id)

    assert done is not None
    assert done.risk_level == "BAIXO"
    assert done.alerts == []


@pytest.mark.parametrize(
    ("fixture_name", "expected_level"),
    [
        ("vitals_medium.csv", "MEDIO"),
        ("vitals_high.csv", "ALTO"),
    ],
)
def test_medio_or_alto_creates_alert_v1(
    fixture_name: str,
    expected_level: str,
) -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_case_with_fixture(
        case_store=case_store,
        blob_store=blob_store,
        fixture_name=fixture_name,
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)

    done = process_vitals_for_case(case_id)

    assert done is not None
    assert done.risk_level == expected_level
    assert len(done.alerts) == 1
    alert = done.alerts[0]
    assert alert.case_id == case_id
    assert alert.level == expected_level
    assert alert.version == 1


def test_worker_reprocess_does_not_duplicate_alert() -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    outbox_store = InMemoryOutboxStore()
    case_id = _seed_case_with_fixture(
        case_store=case_store,
        blob_store=blob_store,
        fixture_name="vitals_medium.csv",
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
    process_modality(str(case_id), "vitals", outbox_job_id=str(job.id))
    process_vitals_for_case(case_id)

    done = case_store.get(case_id)
    assert done is not None
    assert done.risk_level == "MEDIO"
    assert len(done.alerts) == 1
    assert done.alerts[0].version == 1
    assert done.alerts[0].level == "MEDIO"


def test_get_case_exposes_persisted_alerts() -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_case_with_fixture(
        case_store=case_store,
        blob_store=blob_store,
        fixture_name="vitals_high.csv",
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)
    process_vitals_for_case(case_id)

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

    assert response.risk_level == "ALTO"
    assert len(response.alerts) == 1
    assert response.alerts[0].level == "ALTO"
    assert response.alerts[0].version == 1
    assert response.alerts[0].case_id == case_id


def test_alert_model_unique_case_level_version() -> None:
    from sqlalchemy import inspect

    import app.patients.models  # noqa: F401
    from app.cases.models import Alert

    cols = {c.key for c in inspect(Alert).mapper.column_attrs}
    assert cols >= {"id", "case_id", "level", "version", "created_at"}

    fk = next(iter(inspect(Alert).mapper.columns["case_id"].foreign_keys))
    assert fk.column.table.name == "cases"
    assert fk.ondelete == "CASCADE"

    table = Alert.__table__
    unique_sets = [set(c.columns.keys()) for c in table.constraints if hasattr(c, "columns")]
    assert {"case_id", "level", "version"} in unique_sets
