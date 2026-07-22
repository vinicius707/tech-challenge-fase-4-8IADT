"""TDD T5.5 — filas RQ `default` e `video` (Compose + roteamento)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.outbox import completion as completion_mod
from app.outbox.jobs import process_modality
from app.outbox.rq_client import (
    DEFAULT_QUEUE_NAME,
    VIDEO_QUEUE_NAME,
    resolve_queue,
)
from app.outbox.service import (
    InMemoryOutboxStore,
    OutboxDispatcher,
    RecordingJobEnqueuer,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def reset_completion_store() -> None:
    completion_mod.configure_completion_store(None)
    yield
    completion_mod.configure_completion_store(None)


@pytest.mark.parametrize(
    ("modality", "expected_queue"),
    [
        ("vitals", DEFAULT_QUEUE_NAME),
        ("audio", DEFAULT_QUEUE_NAME),
        ("video", VIDEO_QUEUE_NAME),
    ],
)
def test_resolve_queue_routes_by_modality(
    modality: str,
    expected_queue: str,
) -> None:
    assert (
        resolve_queue(
            job_type="process_modality",
            payload={"modality": modality, "case_id": str(uuid.uuid4())},
        )
        == expected_queue
    )


def test_vitals_enqueue_stays_on_default_queue() -> None:
    enqueuer = RecordingJobEnqueuer()
    dispatcher = OutboxDispatcher(store=InMemoryOutboxStore(), enqueuer=enqueuer)
    case_id = uuid.uuid4()
    job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "vitals"},
    )
    dispatcher.try_enqueue(job.id)

    assert len(enqueuer.jobs) == 1
    assert enqueuer.jobs[0]["queue"] == DEFAULT_QUEUE_NAME
    assert enqueuer.jobs[0]["payload"]["modality"] == "vitals"


def test_video_stub_enqueue_uses_video_queue() -> None:
    enqueuer = RecordingJobEnqueuer()
    dispatcher = OutboxDispatcher(store=InMemoryOutboxStore(), enqueuer=enqueuer)
    case_id = uuid.uuid4()
    job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "video"},
    )
    dispatcher.try_enqueue(job.id)

    assert len(enqueuer.jobs) == 1
    assert enqueuer.jobs[0]["queue"] == VIDEO_QUEUE_NAME
    assert enqueuer.jobs[0]["payload"]["modality"] == "video"


def test_video_stub_job_marks_outbox_processed() -> None:
    store = InMemoryOutboxStore()
    dispatcher = OutboxDispatcher(store=store, enqueuer=RecordingJobEnqueuer())
    case_id = uuid.uuid4()
    job = dispatcher.create_pending(
        aggregate_type="case",
        aggregate_id=case_id,
        job_type="process_modality",
        payload={"case_id": str(case_id), "modality": "video"},
    )
    dispatcher.try_enqueue(job.id)
    completion_mod.configure_completion_store(store)

    process_modality(str(case_id), "video", outbox_job_id=str(job.id))

    assert store.get(job.id).status == "processed"


def test_compose_defines_default_and_video_workers() -> None:
    compose_text = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "\n  worker:" in compose_text
    assert "\n  worker-video:" in compose_text
    assert "RQ_QUEUE_NAME" in compose_text
    # Worker default continua em `default`; worker-video escuta `video`.
    assert 'RQ_QUEUE_NAME:-default' in compose_text or "RQ_QUEUE_NAME:-default" in compose_text
    assert "video" in compose_text
    # Comando RQ referencia a fila do ambiente.
    assert "rq worker" in compose_text
