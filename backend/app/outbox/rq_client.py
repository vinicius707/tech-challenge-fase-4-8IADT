from __future__ import annotations

import os
from typing import Any

from redis import Redis
from rq import Queue

DEFAULT_QUEUE_NAME = "default"


def queue_name() -> str:
    return os.getenv("RQ_QUEUE_NAME", DEFAULT_QUEUE_NAME)


def redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_default_queue(connection: Redis | None = None) -> Queue:
    conn = connection or Redis.from_url(redis_url())
    return Queue(queue_name(), connection=conn)


def enqueue_process_modality(
    *,
    case_id: str,
    modality: str,
    outbox_job_id: str | None = None,
    connection: Redis | None = None,
) -> str:
    """Enfileira `process_modality` na fila configurada; retorna o id do job RQ."""
    from app.outbox.jobs import process_modality

    queue = get_default_queue(connection=connection)
    job = queue.enqueue(
        process_modality,
        case_id,
        modality,
        outbox_job_id,
    )
    return str(job.id)


class RqJobEnqueuer:
    """Enqueuer real contra Redis/RQ (fila `default` por padrão)."""

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
