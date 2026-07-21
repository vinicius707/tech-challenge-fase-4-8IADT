from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.patients.schemas import PatientResponse


@dataclass
class PatientRecord:
    id: uuid.UUID
    code: str
    sensitive_label_ciphertext: str | None
    created_at: datetime
    updated_at: datetime


class PatientStore(Protocol):
    def save(self, patient: PatientRecord) -> None: ...

    def get_by_id(self, patient_id: uuid.UUID) -> PatientRecord | None: ...

    def list_all(self) -> list[PatientRecord]: ...

    def delete(self, patient_id: uuid.UUID) -> bool: ...

    def next_code_number(self) -> int: ...


@dataclass
class InMemoryPatientStore:
    _by_id: dict[uuid.UUID, PatientRecord] = field(default_factory=dict)

    def save(self, patient: PatientRecord) -> None:
        self._by_id[patient.id] = patient

    def get_by_id(self, patient_id: uuid.UUID) -> PatientRecord | None:
        return self._by_id.get(patient_id)

    def list_all(self) -> list[PatientRecord]:
        return sorted(self._by_id.values(), key=lambda p: p.code)

    def delete(self, patient_id: uuid.UUID) -> bool:
        return self._by_id.pop(patient_id, None) is not None

    def next_code_number(self) -> int:
        if not self._by_id:
            return 1
        numbers = []
        for patient in self._by_id.values():
            suffix = patient.code.removeprefix("PAC-")
            if suffix.isdigit():
                numbers.append(int(suffix))
        return max(numbers, default=0) + 1


def _to_response(patient: PatientRecord) -> PatientResponse:
    has_label = patient.sensitive_label_ciphertext is not None
    return PatientResponse(
        id=patient.id,
        code=patient.code,
        has_sensitive_label=has_label,
        sensitive_label_masked="********" if has_label else None,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


class PatientService:
    def __init__(self, *, store: PatientStore) -> None:
        self._store = store

    def create(self) -> PatientResponse:
        now = datetime.now(tz=UTC)
        number = self._store.next_code_number()
        patient = PatientRecord(
            id=uuid.uuid4(),
            code=f"PAC-{number:03d}",
            sensitive_label_ciphertext=None,
            created_at=now,
            updated_at=now,
        )
        self._store.save(patient)
        return _to_response(patient)

    def list_patients(self) -> list[PatientResponse]:
        return [_to_response(p) for p in self._store.list_all()]

    def get(self, patient_id: uuid.UUID) -> PatientResponse | None:
        patient = self._store.get_by_id(patient_id)
        if patient is None:
            return None
        return _to_response(patient)

    def update(self, patient_id: uuid.UUID) -> PatientResponse | None:
        patient = self._store.get_by_id(patient_id)
        if patient is None:
            return None
        patient.updated_at = datetime.now(tz=UTC)
        self._store.save(patient)
        return _to_response(patient)

    def delete(self, patient_id: uuid.UUID) -> bool:
        return self._store.delete(patient_id)


_default_store = InMemoryPatientStore()


def get_patient_service() -> PatientService:
    return PatientService(store=_default_store)
