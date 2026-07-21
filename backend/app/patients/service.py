from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.patients.audit import (
    AuditStore,
    InMemoryAuditStore,
    new_reveal_audit,
)
from app.patients.crypto import PiiKeyUnavailableError, SensitiveLabelCipher
from app.patients.schemas import PatientResponse, SensitiveLabelRevealResponse


class PatientNotFoundError(Exception):
    pass


class SensitiveLabelUnavailableError(Exception):
    pass


class _CaseCascadeStore(Protocol):
    def delete_by_patient(self, patient_id: uuid.UUID) -> int: ...


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


def _normalize_label(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


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
    def __init__(
        self,
        *,
        store: PatientStore,
        audit_store: AuditStore | None = None,
        case_store: _CaseCascadeStore | None = None,
        cipher: SensitiveLabelCipher | None = None,
    ) -> None:
        self._store = store
        self._audit_store = audit_store or InMemoryAuditStore()
        if case_store is None:
            from app.cases.service import InMemoryCaseStore

            case_store = InMemoryCaseStore()
        self._case_store = case_store
        self._cipher = cipher or SensitiveLabelCipher.from_environment()

    def create(self, *, sensitive_label: str | None = None) -> PatientResponse:
        ciphertext = self._encrypt_optional(sensitive_label)
        now = datetime.now(tz=UTC)
        number = self._store.next_code_number()
        patient = PatientRecord(
            id=uuid.uuid4(),
            code=f"PAC-{number:03d}",
            sensitive_label_ciphertext=ciphertext,
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

    def update(
        self,
        patient_id: uuid.UUID,
        *,
        sensitive_label: str | None = None,
        update_sensitive_label: bool = False,
    ) -> PatientResponse | None:
        patient = self._store.get_by_id(patient_id)
        if patient is None:
            return None
        if update_sensitive_label:
            patient.sensitive_label_ciphertext = self._encrypt_optional(sensitive_label)
        patient.updated_at = datetime.now(tz=UTC)
        self._store.save(patient)
        return _to_response(patient)

    def delete(self, patient_id: uuid.UUID) -> bool:
        deleted = self._store.delete(patient_id)
        if deleted:
            self._audit_store.delete_by_patient(patient_id)
            self._case_store.delete_by_patient(patient_id)
        return deleted

    def reveal(
        self, patient_id: uuid.UUID, *, operator_id: uuid.UUID
    ) -> SensitiveLabelRevealResponse:
        patient = self._store.get_by_id(patient_id)
        if patient is None:
            raise PatientNotFoundError()
        if patient.sensitive_label_ciphertext is None:
            raise SensitiveLabelUnavailableError()

        plaintext = self._cipher.decrypt(patient.sensitive_label_ciphertext)
        audit = new_reveal_audit(operator_id=operator_id, patient_id=patient_id)
        self._audit_store.append(audit)
        return SensitiveLabelRevealResponse(
            id=patient.id,
            code=patient.code,
            sensitive_label=plaintext,
            revealed_at=audit.created_at,
        )

    def _encrypt_optional(self, sensitive_label: str | None) -> str | None:
        normalized = _normalize_label(sensitive_label)
        if normalized is None:
            return None
        return self._cipher.encrypt(normalized)


_default_store = InMemoryPatientStore()
_default_audit_store = InMemoryAuditStore()


def get_patient_service() -> PatientService:
    from app.cases.service import _default_case_store

    return PatientService(
        store=_default_store,
        audit_store=_default_audit_store,
        case_store=_default_case_store,
    )
