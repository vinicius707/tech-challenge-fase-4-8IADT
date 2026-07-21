"""Outbox leve: grava no store antes de falar com Redis/RQ."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


ELIGIBLE_STATUSES = ("pending", "enqueue_failed")


@dataclass
class OutboxRecord:
    id: uuid.UUID
    aggregate_type: str
    aggregate_id: uuid.UUID
    job_type: str
    payload: dict[str, Any]
    status: str
    rq_job_id: str | None
    attempts: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class OutboxStore(Protocol):
    def save(self, record: OutboxRecord) -> OutboxRecord: ...

    def get(self, job_id: uuid.UUID) -> OutboxRecord | None: ...

    def list_by_statuses(self, statuses: tuple[str, ...]) -> list[OutboxRecord]: ...


class JobEnqueuer(Protocol):
    def enqueue(self, *, job_type: str, payload: dict[str, Any]) -> str:
        """Retorna o `rq_job_id`. Levanta exceção se Redis/RQ falhar."""
        ...


@dataclass
class InMemoryOutboxStore:
    _by_id: dict[uuid.UUID, OutboxRecord] = field(default_factory=dict)

    def save(self, record: OutboxRecord) -> OutboxRecord:
        self._by_id[record.id] = record
        return record

    def get(self, job_id: uuid.UUID) -> OutboxRecord | None:
        return self._by_id.get(job_id)

    def list_by_statuses(self, statuses: tuple[str, ...]) -> list[OutboxRecord]:
        allowed = set(statuses)
        return [r for r in self._by_id.values() if r.status in allowed]


@dataclass
class RecordingJobEnqueuer:
    """Fake de RQ: registra jobs na fila nomeada (padrão `default`)."""

    queue_name: str = "default"
    jobs: list[dict[str, Any]] = field(default_factory=list)

    def enqueue(self, *, job_type: str, payload: dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        self.jobs.append(
            {
                "rq_job_id": job_id,
                "queue": self.queue_name,
                "job_type": job_type,
                "payload": payload,
            }
        )
        return job_id


@dataclass
class FailingJobEnqueuer:
    message: str = "Redis unavailable"

    def enqueue(self, *, job_type: str, payload: dict[str, Any]) -> str:
        raise ConnectionError(self.message)


class OutboxDispatcher:
    def __init__(self, store: OutboxStore, enqueuer: JobEnqueuer) -> None:
        self._store = store
        self._enqueuer = enqueuer

    def create_pending(
        self,
        *,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        job_type: str,
        payload: dict[str, Any],
    ) -> OutboxRecord:
        now = datetime.now(tz=UTC)
        record = OutboxRecord(
            id=uuid.uuid4(),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            job_type=job_type,
            payload=payload,
            status="pending",
            rq_job_id=None,
            attempts=0,
            last_error=None,
            created_at=now,
            updated_at=now,
        )
        return self._store.save(record)

    def try_enqueue(self, job_id: uuid.UUID) -> OutboxRecord:
        record = self._store.get(job_id)
        if record is None:
            raise KeyError(f"outbox job not found: {job_id}")

        now = datetime.now(tz=UTC)
        attempts = record.attempts + 1
        enqueue_payload = {
            **record.payload,
            "outbox_job_id": str(record.id),
        }
        try:
            rq_job_id = self._enqueuer.enqueue(
                job_type=record.job_type,
                payload=enqueue_payload,
            )
        except Exception as exc:  # noqa: BLE001 — falha de broker vira enqueue_failed
            failed = OutboxRecord(
                id=record.id,
                aggregate_type=record.aggregate_type,
                aggregate_id=record.aggregate_id,
                job_type=record.job_type,
                payload=record.payload,
                status="enqueue_failed",
                rq_job_id=None,
                attempts=attempts,
                last_error=str(exc),
                created_at=record.created_at,
                updated_at=now,
            )
            return self._store.save(failed)

        enqueued = OutboxRecord(
            id=record.id,
            aggregate_type=record.aggregate_type,
            aggregate_id=record.aggregate_id,
            job_type=record.job_type,
            payload=record.payload,
            status="enqueued",
            rq_job_id=rq_job_id,
            attempts=attempts,
            last_error=None,
            created_at=record.created_at,
            updated_at=now,
        )
        return self._store.save(enqueued)

    def mark_processed(self, job_id: uuid.UUID) -> OutboxRecord:
        record = self._store.get(job_id)
        if record is None:
            raise KeyError(f"outbox job not found: {job_id}")
        if record.status == "processed":
            return record

        now = datetime.now(tz=UTC)
        processed = OutboxRecord(
            id=record.id,
            aggregate_type=record.aggregate_type,
            aggregate_id=record.aggregate_id,
            job_type=record.job_type,
            payload=record.payload,
            status="processed",
            rq_job_id=record.rq_job_id,
            attempts=record.attempts,
            last_error=None,
            created_at=record.created_at,
            updated_at=now,
        )
        return self._store.save(processed)
