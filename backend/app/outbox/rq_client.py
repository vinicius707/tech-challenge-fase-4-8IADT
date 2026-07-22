from __future__ import annotations

import os
from typing import Any

from redis import Redis
from rq import Queue

DEFAULT_QUEUE_NAME = "default"
VIDEO_QUEUE_NAME = "video"


def queue_name() -> str:
    """Fila que este processo worker escuta (`RQ_QUEUE_NAME`)."""
    return os.getenv("RQ_QUEUE_NAME", DEFAULT_QUEUE_NAME)


def video_queue_name() -> str:
    return os.getenv("RQ_VIDEO_QUEUE_NAME", VIDEO_QUEUE_NAME)


def redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def resolve_queue(*, job_type: str, payload: dict[str, Any]) -> str:
    """Roteia jobs: modalidade `video` → fila `video`; demais → `default`."""
    if job_type == "process_video_stub":
        return video_queue_name()
    modality = str(payload.get("modality") or "")
    if modality == "video":
        return video_queue_name()
    return DEFAULT_QUEUE_NAME


def get_queue(name: str, connection: Redis | None = None) -> Queue:
    conn = connection or Redis.from_url(redis_url())
    return Queue(name, connection=conn)


def get_default_queue(connection: Redis | None = None) -> Queue:
    """Compat: fila que o worker escuta (env), não o roteamento por modalidade."""
    return get_queue(queue_name(), connection=connection)


def enqueue_process_modality(
    *,
    case_id: str,
    modality: str,
    outbox_job_id: str | None = None,
    connection: Redis | None = None,
) -> str:
    """Enfileira `process_modality` na fila correta; retorna o id do job RQ."""
    from app.outbox.jobs import process_modality

    qname = resolve_queue(
        job_type="process_modality",
        payload={"case_id": case_id, "modality": modality},
    )
    queue = get_queue(qname, connection=connection)
    from app.outbox.timeouts import modality_timeout_seconds

    job = queue.enqueue(
        process_modality,
        case_id,
        modality,
        outbox_job_id,
        job_timeout=int(modality_timeout_seconds(modality)),
    )
    return str(job.id)


class RqJobEnqueuer:
    """Enqueuer real contra Redis/RQ (roteia `video` vs `default`)."""

    def enqueue(self, *, job_type: str, payload: dict[str, Any]) -> str:
        if job_type != "process_modality":
            raise ValueError(f"job_type não suportado: {job_type}")
        return enqueue_process_modality(
            case_id=str(payload["case_id"]),
            modality=str(payload["modality"]),
            outbox_job_id=(
                str(payload["outbox_job_id"])
                if payload.get("outbox_job_id") is not None
                else None
            ),
        )
