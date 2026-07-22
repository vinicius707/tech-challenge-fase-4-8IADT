"""TDD T6.18 — worker real de prescriptions + fusão de Risco / falha parcial."""

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
from app.outbox.rq_client import DEFAULT_QUEUE_NAME, VIDEO_QUEUE_NAME, resolve_queue
from app.outbox.service import (
    InMemoryOutboxStore,
    OutboxDispatcher,
    RecordingJobEnqueuer,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"
RX_DIR = REPO_ROOT / "data" / "fixtures" / "prescriptions"


@pytest.fixture(autouse=True)
def reset_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    monkeypatch.delenv("LIMEN_FORCE_FAIL_MODALITIES", raising=False)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def _seed_vitals_and_prescriptions(
    *,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    vitals_fixture: str = "vitals_medium.csv",
    rx_fixture: str = "prescriptions_normal.csv",
    patient_id: uuid.UUID | None = None,
) -> uuid.UUID:
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    patient = patient_id or uuid.uuid4()
    vitals_id = uuid.uuid4()
    rx_id = uuid.uuid4()
    vitals_key = f"cases/{case_id}/vitals/{vitals_fixture}"
    rx_key = f"cases/{case_id}/prescriptions/{rx_fixture}"
    blob_store.put(
        bucket="limen",
        object_key=vitals_key,
        content=(VITALS_DIR / vitals_fixture).read_bytes(),
        content_type="text/csv",
    )
    blob_store.put(
        bucket="limen",
        object_key=rx_key,
        content=(RX_DIR / rx_fixture).read_bytes(),
        content_type="text/csv",
    )
    case_store.save(
        CaseRecord(
            id=case_id,
            patient_id=patient,
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
                    modality="prescriptions",
                    status="pending",
                    artifact_id=rx_id,
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
                    id=rx_id,
                    case_id=case_id,
                    modality="prescriptions",
                    bucket="limen",
                    object_key=rx_key,
                    content_sha256="x",
                    content_type="text/csv",
                    created_at=now,
                ),
            ],
        )
    )
    return case_id


def test_prescriptions_job_routes_to_default_queue_not_video() -> None:
    assert (
        resolve_queue(
            job_type="process_modality",
            payload={"case_id": str(uuid.uuid4()), "modality": "prescriptions"},
        )
        == DEFAULT_QUEUE_NAME
    )
    assert (
        resolve_queue(
            job_type="process_modality",
            payload={"case_id": str(uuid.uuid4()), "modality": "prescriptions"},
        )
        != VIDEO_QUEUE_NAME
    )


def test_fusion_vitals_and_prescriptions_done_considers_both() -> None:
    """Cenário 4: vitals + prescriptions done → Risco fundido (não só vitais)."""
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_vitals_and_prescriptions(
        case_store=case_store,
        blob_store=blob_store,
        vitals_fixture="vitals_medium.csv",
        rx_fixture="prescriptions_normal.csv",
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)

    process_modality_for_case(case_id, "vitals")
    mid = case_store.get(case_id)
    assert mid is not None
    assert mid.status == "processing"
    assert mid.risk_level is None

    process_modality_for_case(case_id, "prescriptions")
    done = case_store.get(case_id)
    assert done is not None
    by_mod = {m.modality: m.status for m in done.modalities}
    assert by_mod == {"vitals": "done", "prescriptions": "done"}
    assert done.status == "done"
    # vitals MEDIO 0.55 + prescriptions BAIXO 0.10 → média 0.325 BAIXO
    # (se só vitais: MEDIO 0.55 — prova que a fusão considera prescriptions).
    assert done.risk_score == pytest.approx(0.325)
    assert done.risk_level == "BAIXO"


def test_partial_failure_prescriptions_failed_vitals_done_closes_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cenário 4: prescriptions failed + vitals done → Caso done (falha parcial)."""
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    outbox_store = InMemoryOutboxStore()
    case_id = _seed_vitals_and_prescriptions(
        case_store=case_store,
        blob_store=blob_store,
        vitals_fixture="vitals_medium.csv",
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)
    completion_mod.configure_completion_store(outbox_store)
    monkeypatch.setenv("LIMEN_FORCE_FAIL_MODALITIES", "prescriptions")

    dispatcher = OutboxDispatcher(store=outbox_store, enqueuer=RecordingJobEnqueuer())
    vitals_job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "vitals"},
    )
    rx_job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "prescriptions"},
    )
    dispatcher.try_enqueue(vitals_job.id)
    dispatcher.try_enqueue(rx_job.id)

    process_modality(str(case_id), "vitals", outbox_job_id=str(vitals_job.id))
    process_modality(str(case_id), "prescriptions", outbox_job_id=str(rx_job.id))

    done = case_store.get(case_id)
    assert done is not None
    by_mod = {m.modality: m.status for m in done.modalities}
    assert by_mod == {"vitals": "done", "prescriptions": "failed"}
    assert done.status == "done"
    assert done.risk_level == "MEDIO"
    assert done.risk_score is not None
    assert 0.40 <= done.risk_score < 0.70
    assert outbox_store.get(vitals_job.id).status == "processed"
    assert outbox_store.get(rx_job.id).status == "processed"


def test_worker_applies_longitudinal_history_from_prior_case() -> None:
    """Cenário 3 via worker: histórico do Paciente eleva risco com desvio de dose."""
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    patient_id = uuid.uuid4()
    prior_id = _seed_vitals_and_prescriptions(
        case_store=case_store,
        blob_store=blob_store,
        vitals_fixture="vitals_normal.csv",
        rx_fixture="prescriptions_normal.csv",
        patient_id=patient_id,
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)
    process_modality_for_case(prior_id, "vitals")
    process_modality_for_case(prior_id, "prescriptions")
    prior = case_store.get(prior_id)
    assert prior is not None
    assert prior.status == "done"

    # Novo Caso: metformin 1500 (na faixa, mas >50% vs histórico 500).
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    rx_id = uuid.uuid4()
    csv_bytes = (
        b"timestamp,medication,dose_mg,interval_hours,label\n"
        b"0000,metformin,1500.00,12.00,normal\n"
    )
    object_key = f"cases/{case_id}/prescriptions/rx_deviated.csv"
    blob_store.put(
        bucket="limen",
        object_key=object_key,
        content=csv_bytes,
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
            content_sha256="y",
            created_at=now,
            updated_at=now,
            modalities=[
                ModalityRecord(
                    id=uuid.uuid4(),
                    case_id=case_id,
                    modality="prescriptions",
                    status="pending",
                    artifact_id=rx_id,
                    created_at=now,
                    updated_at=now,
                )
            ],
            artifacts=[
                ArtifactRecord(
                    id=rx_id,
                    case_id=case_id,
                    modality="prescriptions",
                    bucket="limen",
                    object_key=object_key,
                    content_sha256="y",
                    content_type="text/csv",
                    created_at=now,
                )
            ],
        )
    )

    process_modality_for_case(case_id, "prescriptions")
    done = case_store.get(case_id)
    assert done is not None
    assert done.status == "done"
    assert done.risk_level == "MEDIO"
    assert done.risk_score == pytest.approx(0.55)
