"""TDD T5.1 — store compartilhado Caso/outbox entre processos API e worker."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.cases import runtime as runtime_mod
from app.cases.db_store import SqlAlchemyCaseStore
from app.cases.service import (
    ArtifactRecord,
    CaseRecord,
    ModalityRecord,
)
from app.cases.storage import InMemoryArtifactBlobStore
from app.db import Base
from app.outbox import completion as completion_mod
from app.outbox.db_store import SqlAlchemyOutboxStore
from app.outbox.jobs import process_modality
from app.outbox.service import OutboxDispatcher, RecordingJobEnqueuer
from app.patients.db_store import SqlAlchemyPatientStore
from app.patients.service import PatientRecord

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_CSV = (REPO_ROOT / "data" / "fixtures" / "vitals" / "vitals_normal.csv").read_bytes()


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    """SQLite em memória simula o Postgres compartilhado API↔worker."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    from app.cases.models import Alert, Artifact, Case, CaseModality
    from app.outbox.models import OutboxJob
    from app.patients.models import Patient

    Base.metadata.create_all(
        engine,
        tables=[
            Patient.__table__,
            Case.__table__,
            Artifact.__table__,
            CaseModality.__table__,
            Alert.__table__,
            OutboxJob.__table__,
        ],
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def reset_runtime() -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def _seed_patient(factory: sessionmaker[Session]) -> PatientRecord:
    store = SqlAlchemyPatientStore(session_factory=factory)
    now = datetime.now(tz=UTC)
    patient = PatientRecord(
        id=uuid.uuid4(),
        code="PAC-001",
        sensitive_label_ciphertext=None,
        created_at=now,
        updated_at=now,
    )
    store.save(patient)
    return patient


def _pending_case(patient_id: uuid.UUID) -> CaseRecord:
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    return CaseRecord(
        id=case_id,
        patient_id=patient_id,
        status="pending",
        risk_score=None,
        risk_level=None,
        idempotency_key=f"idem-{case_id}",
        content_sha256="abc",
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
                object_key=f"cases/{case_id}/vitals/vitals.csv",
                content_sha256="abc",
                content_type="text/csv",
                created_at=now,
            )
        ],
        alerts=[],
    )


def test_case_saved_by_api_store_is_visible_to_worker_store(
    session_factory: sessionmaker[Session],
) -> None:
    patient = _seed_patient(session_factory)
    api_store = SqlAlchemyCaseStore(session_factory=session_factory)
    worker_store = SqlAlchemyCaseStore(session_factory=session_factory)

    case = _pending_case(patient.id)
    api_store.save(case)

    loaded = worker_store.get(case.id)
    assert loaded is not None
    assert loaded.status == "pending"
    assert loaded.modalities[0].status == "pending"
    assert len(loaded.artifacts) == 1


def test_worker_case_update_is_visible_to_api_store(
    session_factory: sessionmaker[Session],
) -> None:
    patient = _seed_patient(session_factory)
    api_store = SqlAlchemyCaseStore(session_factory=session_factory)
    worker_store = SqlAlchemyCaseStore(session_factory=session_factory)

    case = _pending_case(patient.id)
    api_store.save(case)

    worker_view = worker_store.get(case.id)
    assert worker_view is not None
    now = datetime.now(tz=UTC)
    updated_mods = [
        ModalityRecord(
            id=m.id,
            case_id=m.case_id,
            modality=m.modality,
            status="done",
            artifact_id=m.artifact_id,
            created_at=m.created_at,
            updated_at=now,
        )
        for m in worker_view.modalities
    ]
    worker_store.save(
        CaseRecord(
            id=worker_view.id,
            patient_id=worker_view.patient_id,
            status="done",
            risk_score=0.1,
            risk_level="BAIXO",
            idempotency_key=worker_view.idempotency_key,
            content_sha256=worker_view.content_sha256,
            created_at=worker_view.created_at,
            updated_at=now,
            modalities=updated_mods,
            artifacts=worker_view.artifacts,
            alerts=worker_view.alerts,
        )
    )

    api_view = api_store.get(case.id)
    assert api_view is not None
    assert api_view.status == "done"
    assert api_view.risk_level == "BAIXO"
    assert api_view.modalities[0].status == "done"


def test_outbox_saved_by_api_is_visible_and_completable_by_worker(
    session_factory: sessionmaker[Session],
) -> None:
    api_outbox = SqlAlchemyOutboxStore(session_factory=session_factory)
    worker_outbox = SqlAlchemyOutboxStore(session_factory=session_factory)
    case_id = uuid.uuid4()

    dispatcher = OutboxDispatcher(store=api_outbox, enqueuer=RecordingJobEnqueuer())
    job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "vitals"},
    )
    dispatcher.try_enqueue(job.id)

    seen = worker_outbox.get(job.id)
    assert seen is not None
    assert seen.status == "enqueued"

    completion_mod.configure_completion_store(worker_outbox)
    process_modality(str(case_id), "vitals", outbox_job_id=str(job.id))

    assert api_outbox.get(job.id).status == "processed"


def test_worker_processes_case_from_shared_sql_store_without_prior_configure(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simula o processo RQ: sem configure_case_runtime prévio, usa store SQL."""
    patient = _seed_patient(session_factory)
    case_store = SqlAlchemyCaseStore(session_factory=session_factory)
    outbox_store = SqlAlchemyOutboxStore(session_factory=session_factory)
    blob_store = InMemoryArtifactBlobStore()

    case = _pending_case(patient.id)
    blob_store.put(
        bucket=case.artifacts[0].bucket,
        object_key=case.artifacts[0].object_key,
        content=VITALS_CSV,
        content_type="text/csv",
    )
    case_store.save(case)

    dispatcher = OutboxDispatcher(store=outbox_store, enqueuer=RecordingJobEnqueuer())
    job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case.id,
        job_type="process_modality",
        payload={"case_id": str(case.id), "modality": "vitals"},
    )
    dispatcher.try_enqueue(job.id)

    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setattr(
        "app.cases.runtime.build_shared_case_runtime",
        lambda: runtime_mod.CaseRuntime(
            case_store=case_store,
            blob_store=blob_store,
        ),
    )
    completion_mod.configure_completion_store(outbox_store)

    # Sem configure_case_runtime — o worker auto-monta o runtime compartilhado.
    assert runtime_mod._case_store is None
    assert runtime_mod._blob_store is None
    runtime = runtime_mod.get_case_runtime()
    assert runtime is not None
    assert runtime.case_store is case_store

    process_modality(str(case.id), "vitals", outbox_job_id=str(job.id))

    done = case_store.get(case.id)
    assert done is not None
    assert done.status == "done"
    assert done.modalities[0].status == "done"
    assert done.risk_level == "BAIXO"
    assert outbox_store.get(job.id).status == "processed"


def test_compose_backend_and_worker_share_postgres_url() -> None:
    compose_text = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "\n  backend:" in compose_text
    assert "\n  worker:" in compose_text
    assert compose_text.count("POSTGRES_URL: postgresql://") >= 2
    # Mesmo host/serviço de banco para API e worker.
    assert "@postgres:5432/" in compose_text
