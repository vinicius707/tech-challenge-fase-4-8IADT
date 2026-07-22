from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

REVEAL_SENSITIVE_LABEL = "reveal_sensitive_label"
DLQ_REDRIVE = "dlq_redrive"
DLQ_DISCARD = "dlq_discard"


@dataclass(frozen=True)
class AuditRecord:
    id: uuid.UUID
    operator_id: uuid.UUID
    patient_id: uuid.UUID
    action: str
    created_at: datetime


class AuditStore(Protocol):
    def append(self, record: AuditRecord) -> None: ...

    def list_by_patient(self, patient_id: uuid.UUID) -> list[AuditRecord]: ...

    def delete_by_patient(self, patient_id: uuid.UUID) -> int: ...


@dataclass
class InMemoryAuditStore:
    _records: list[AuditRecord] = field(default_factory=list)

    def append(self, record: AuditRecord) -> None:
        self._records.append(record)

    def list_by_patient(self, patient_id: uuid.UUID) -> list[AuditRecord]:
        return [r for r in self._records if r.patient_id == patient_id]

    def delete_by_patient(self, patient_id: uuid.UUID) -> int:
        before = len(self._records)
        self._records = [r for r in self._records if r.patient_id != patient_id]
        return before - len(self._records)


def new_reveal_audit(
    *, operator_id: uuid.UUID, patient_id: uuid.UUID
) -> AuditRecord:
    return AuditRecord(
        id=uuid.uuid4(),
        operator_id=operator_id,
        patient_id=patient_id,
        action=REVEAL_SENSITIVE_LABEL,
        created_at=datetime.now(tz=UTC),
    )
