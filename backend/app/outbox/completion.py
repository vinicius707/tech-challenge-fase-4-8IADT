"""Conclusão idempotente de jobs do outbox após o worker processar."""

from __future__ import annotations

import uuid

from app.outbox.service import OutboxDispatcher, OutboxStore

_completion_store: OutboxStore | None = None


def configure_completion_store(store: OutboxStore | None) -> None:
    global _completion_store
    _completion_store = store


def get_completion_store() -> OutboxStore:
    if _completion_store is not None:
        return _completion_store
    from app.outbox.db_store import SqlAlchemyOutboxStore

    return SqlAlchemyOutboxStore()


def complete_job(job_id: uuid.UUID) -> None:
    store = get_completion_store()
    # Enqueuer não é usado em mark_processed; Recording evita import circular com RQ.
    from app.outbox.service import RecordingJobEnqueuer

    OutboxDispatcher(store=store, enqueuer=RecordingJobEnqueuer()).mark_processed(job_id)
