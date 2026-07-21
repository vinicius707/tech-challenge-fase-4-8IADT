"""Store Postgres para outbox (worker / reconciler em runtime)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_session_factory
from app.outbox.models import OutboxJob
from app.outbox.service import OutboxRecord


def _to_record(row: OutboxJob) -> OutboxRecord:
    return OutboxRecord(
        id=row.id,
        aggregate_type=row.aggregate_type,
        aggregate_id=row.aggregate_id,
        job_type=row.job_type,
        payload=dict(row.payload or {}),
        status=row.status,
        rq_job_id=row.rq_job_id,
        attempts=row.attempts,
        last_error=row.last_error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyOutboxStore:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def save(self, record: OutboxRecord) -> OutboxRecord:
        with self._session_factory() as session:
            row = session.get(OutboxJob, record.id)
            if row is None:
                row = OutboxJob(
                    id=record.id,
                    created_at=record.created_at,
                )
                session.add(row)
            row.aggregate_type = record.aggregate_type
            row.aggregate_id = record.aggregate_id
            row.job_type = record.job_type
            row.payload = record.payload
            row.status = record.status
            row.rq_job_id = record.rq_job_id
            row.attempts = record.attempts
            row.last_error = record.last_error
            row.updated_at = record.updated_at or datetime.now(tz=UTC)
            session.commit()
            session.refresh(row)
            return _to_record(row)

    def get(self, job_id: uuid.UUID) -> OutboxRecord | None:
        with self._session_factory() as session:
            row = session.get(OutboxJob, job_id)
            return _to_record(row) if row else None

    def list_by_statuses(self, statuses: tuple[str, ...]) -> list[OutboxRecord]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(OutboxJob)
                .where(OutboxJob.status.in_(statuses))
                .order_by(OutboxJob.created_at.asc())
            ).all()
            return [_to_record(row) for row in rows]
