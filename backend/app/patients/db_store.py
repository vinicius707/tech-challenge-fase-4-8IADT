"""Store Postgres para Paciente (pré-requisito de FK do Caso compartilhado)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_session_factory
from app.patients.models import Patient
from app.patients.service import PatientRecord


def _to_record(row: Patient) -> PatientRecord:
    return PatientRecord(
        id=row.id,
        code=row.code,
        sensitive_label_ciphertext=row.sensitive_label_ciphertext,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyPatientStore:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def save(self, patient: PatientRecord) -> None:
        with self._session_factory() as session:
            row = session.get(Patient, patient.id)
            if row is None:
                row = Patient(id=patient.id, created_at=patient.created_at)
                session.add(row)
            row.code = patient.code
            row.sensitive_label_ciphertext = patient.sensitive_label_ciphertext
            row.updated_at = patient.updated_at
            session.commit()

    def get_by_id(self, patient_id: uuid.UUID) -> PatientRecord | None:
        with self._session_factory() as session:
            row = session.get(Patient, patient_id)
            return _to_record(row) if row else None

    def list_all(self) -> list[PatientRecord]:
        with self._session_factory() as session:
            rows = session.scalars(select(Patient).order_by(Patient.code.asc())).all()
            return [_to_record(row) for row in rows]

    def delete(self, patient_id: uuid.UUID) -> bool:
        with self._session_factory() as session:
            row = session.get(Patient, patient_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    def next_code_number(self) -> int:
        with self._session_factory() as session:
            codes = session.scalars(select(Patient.code)).all()
        numbers: list[int] = []
        for code in codes:
            suffix = code.removeprefix("PAC-")
            if suffix.isdigit():
                numbers.append(int(suffix))
        return max(numbers, default=0) + 1
