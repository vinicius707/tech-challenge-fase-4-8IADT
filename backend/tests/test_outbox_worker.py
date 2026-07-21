"""TDD T3.4 — reconciler outbox + worker marca processed + Compose."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.outbox import completion as completion_mod
from app.outbox.jobs import process_modality
from app.outbox.reconciler import OutboxReconciler
from app.outbox.service import (
    FailingJobEnqueuer,
    InMemoryOutboxStore,
    OutboxDispatcher,
    RecordingJobEnqueuer,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def store() -> InMemoryOutboxStore:
    return InMemoryOutboxStore()


@pytest.fixture
def case_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture(autouse=True)
def reset_completion_store() -> None:
    completion_mod.configure_completion_store(None)
    yield
    completion_mod.configure_completion_store(None)


def test_reconciler_recovers_pending_and_enqueue_failed(
    store: InMemoryOutboxStore,
    case_id: uuid.UUID,
) -> None:
    fail_dispatcher = OutboxDispatcher(store=store, enqueuer=FailingJobEnqueuer())
    pending = fail_dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "vitals"},
    )
    failed = fail_dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=uuid.uuid4(),
        job_type="process_modality",
        payload={"case_id": str(uuid.uuid4()), "modality": "vitals"},
    )
    fail_dispatcher.try_enqueue(failed.id)
    assert store.get(failed.id).status == "enqueue_failed"
    assert store.get(pending.id).status == "pending"

    enqueuer = RecordingJobEnqueuer(queue_name="default")
    dispatcher = OutboxDispatcher(store=store, enqueuer=enqueuer)
    reconciler = OutboxReconciler(dispatcher=dispatcher, store=store)

    results = reconciler.reconcile()

    assert len(results) == 2
    assert all(r.status == "enqueued" for r in results)
    assert all(r.rq_job_id for r in results)
    assert len(enqueuer.jobs) == 2
    assert all(job["queue"] == "default" for job in enqueuer.jobs)


def test_worker_process_modality_marks_outbox_processed(
    store: InMemoryOutboxStore,
    case_id: uuid.UUID,
) -> None:
    enqueuer = RecordingJobEnqueuer()
    dispatcher = OutboxDispatcher(store=store, enqueuer=enqueuer)
    job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "vitals"},
    )
    enqueued = dispatcher.try_enqueue(job.id)
    assert enqueued.status == "enqueued"

    completion_mod.configure_completion_store(store)
    process_modality(
        str(case_id),
        "vitals",
        outbox_job_id=str(job.id),
    )

    done = store.get(job.id)
    assert done is not None
    assert done.status == "processed"


def test_worker_process_modality_is_idempotent_when_already_processed(
    store: InMemoryOutboxStore,
    case_id: uuid.UUID,
) -> None:
    dispatcher = OutboxDispatcher(store=store, enqueuer=RecordingJobEnqueuer())
    job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "vitals"},
    )
    dispatcher.try_enqueue(job.id)
    completion_mod.configure_completion_store(store)
    process_modality(str(case_id), "vitals", outbox_job_id=str(job.id))
    process_modality(str(case_id), "vitals", outbox_job_id=str(job.id))

    assert store.get(job.id).status == "processed"


def test_compose_defines_worker_and_reconciler_on_default_queue() -> None:
    compose_text = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "\n  worker:" in compose_text
    assert "\n  outbox-reconciler:" in compose_text
    assert "rq worker" in compose_text or '"rq", "worker"' in compose_text
    assert "app.outbox.reconciler" in compose_text
    assert "RQ_QUEUE_NAME" in compose_text
