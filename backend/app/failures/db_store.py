"""Store Postgres para Falhas de Processamento."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_session_factory
from app.failures.models import ProcessingFailure
from app.failures.service import FailureRecord


def _to_record(row: ProcessingFailure) -> FailureRecord:
    return FailureRecord(
        id=row.id,
        case_id=row.case_id,
        patient_id=row.patient_id,
        modality=row.modality,
        error_summary=row.error_summary,
        attempts=row.attempts,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyFailureStore:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def save(self, record: FailureRecord) -> FailureRecord:
        with self._session_factory() as session:
            row = session.get(ProcessingFailure, record.id)
            if row is None:
                row = ProcessingFailure(
                    id=record.id,
                    created_at=record.created_at,
                )
                session.add(row)
            row.case_id = record.case_id
            row.patient_id = record.patient_id
            row.modality = record.modality
            row.error_summary = record.error_summary
            row.attempts = record.attempts
            row.status = record.status
            row.updated_at = record.updated_at
            session.commit()
            session.refresh(row)
            return _to_record(row)

    def get(self, failure_id: uuid.UUID) -> FailureRecord | None:
        with self._session_factory() as session:
            row = session.get(ProcessingFailure, failure_id)
            return _to_record(row) if row else None

    def list_open(self) -> list[FailureRecord]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ProcessingFailure)
                .where(ProcessingFailure.status == "open")
                .order_by(ProcessingFailure.created_at.asc())
            ).all()
            return [_to_record(row) for row in rows]
