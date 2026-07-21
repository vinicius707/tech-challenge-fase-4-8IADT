"""Stub mínimo de Caso para fixar patient_id ON DELETE CASCADE.

Fora da API HTTP nesta etapa (Épico 2). O domínio completo de Caso entra no
Épico 3.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass
class CaseStubRecord:
    id: uuid.UUID
    patient_id: uuid.UUID
    created_at: datetime


class CaseStubStore(Protocol):
    def save_for_patient(self, patient_id: uuid.UUID) -> CaseStubRecord: ...

    def list_by_patient(self, patient_id: uuid.UUID) -> list[CaseStubRecord]: ...

    def delete_by_patient(self, patient_id: uuid.UUID) -> int: ...


@dataclass
class InMemoryCaseStubStore:
    _by_id: dict[uuid.UUID, CaseStubRecord] = field(default_factory=dict)

    def save_for_patient(self, patient_id: uuid.UUID) -> CaseStubRecord:
        record = CaseStubRecord(
            id=uuid.uuid4(),
            patient_id=patient_id,
            created_at=datetime.now(tz=UTC),
        )
        self._by_id[record.id] = record
        return record

    def list_by_patient(self, patient_id: uuid.UUID) -> list[CaseStubRecord]:
        return [r for r in self._by_id.values() if r.patient_id == patient_id]

    def delete_by_patient(self, patient_id: uuid.UUID) -> int:
        to_remove = [
            case_id
            for case_id, record in self._by_id.items()
            if record.patient_id == patient_id
        ]
        for case_id in to_remove:
            del self._by_id[case_id]
        return len(to_remove)
