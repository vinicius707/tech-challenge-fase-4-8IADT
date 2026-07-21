"""TDD T3.3 — outbox Postgres + enqueue RQ `default`."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.outbox.service import (
    FailingJobEnqueuer,
    InMemoryOutboxStore,
    OutboxDispatcher,
    RecordingJobEnqueuer,
)


@pytest.fixture
def store() -> InMemoryOutboxStore:
    return InMemoryOutboxStore()


@pytest.fixture
def case_id() -> uuid.UUID:
    return uuid.uuid4()


def test_create_outbox_job_is_pending_with_vitals_payload(
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

    assert job.status == "pending"
    assert job.rq_job_id is None
    assert job.attempts == 0
    assert job.payload == {"case_id": str(case_id), "modality": "vitals"}
    assert store.get(job.id) is not None


def test_enqueue_success_sets_enqueued_and_rq_job_id(
    store: InMemoryOutboxStore,
    case_id: uuid.UUID,
) -> None:
    enqueuer = RecordingJobEnqueuer(queue_name="default")
    dispatcher = OutboxDispatcher(store=store, enqueuer=enqueuer)
    job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "vitals"},
    )

    updated = dispatcher.try_enqueue(job.id)

    assert updated.status == "enqueued"
    assert updated.rq_job_id is not None
    assert updated.attempts == 1
    assert updated.last_error is None
    assert enqueuer.queue_name == "default"
    assert len(enqueuer.jobs) == 1
    assert enqueuer.jobs[0]["payload"]["modality"] == "vitals"
    assert enqueuer.jobs[0]["payload"]["case_id"] == str(case_id)


def test_enqueue_redis_failure_keeps_outbox_recoverable(
    store: InMemoryOutboxStore,
    case_id: uuid.UUID,
) -> None:
    """Falha de Redis não apaga o outbox (domínio permanece recuperável)."""
    domain_alive = {"case_id": case_id}
    dispatcher = OutboxDispatcher(store=store, enqueuer=FailingJobEnqueuer())
    job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "vitals"},
    )

    updated = dispatcher.try_enqueue(job.id)

    assert updated.status == "enqueue_failed"
    assert updated.rq_job_id is None
    assert updated.attempts == 1
    assert updated.last_error
    assert store.get(job.id) is not None
    assert domain_alive["case_id"] == case_id


def test_outbox_job_model_declares_required_columns() -> None:
    from sqlalchemy import inspect

    from app.outbox.models import OutboxJob

    columns = {c.key for c in inspect(OutboxJob).mapper.column_attrs}
    assert columns >= {
        "id",
        "aggregate_type",
        "aggregate_id",
        "job_type",
        "payload",
        "status",
        "rq_job_id",
        "attempts",
        "last_error",
        "created_at",
        "updated_at",
    }


def test_rq_queue_name_defaults_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RQ_QUEUE_NAME", raising=False)
    from app.outbox.rq_client import queue_name

    assert queue_name() == "default"
