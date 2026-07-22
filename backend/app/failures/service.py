"""Serviço de Falhas de Processamento (DLQ) — listagem, redrive e discard."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.cases.service import CaseRecord, CaseStore, ModalityRecord
from app.failures.schemas import FailureResponse
from app.outbox.retries import RetryPolicy
from app.outbox.service import OutboxDispatcher
from app.patients.audit import (
    DLQ_DISCARD,
    DLQ_REDRIVE,
    AuditRecord,
    AuditStore,
    InMemoryAuditStore,
)


class FailureNotFoundError(Exception):
    pass


class FailureNotOpenError(Exception):
    """Falha já redriven/discarded — não elegível para a ação."""


@dataclass
class FailureRecord:
    id: uuid.UUID
    case_id: uuid.UUID
    patient_id: uuid.UUID
    modality: str
    error_summary: str
    attempts: int
    status: str
    created_at: datetime
    updated_at: datetime


class FailureStore(Protocol):
    def save(self, record: FailureRecord) -> FailureRecord: ...

    def get(self, failure_id: uuid.UUID) -> FailureRecord | None: ...

    def list_open(self) -> list[FailureRecord]: ...


@dataclass
class InMemoryFailureStore:
    _by_id: dict[uuid.UUID, FailureRecord] = field(default_factory=dict)

    def save(self, record: FailureRecord) -> FailureRecord:
        self._by_id[record.id] = record
        return record

    def get(self, failure_id: uuid.UUID) -> FailureRecord | None:
        return self._by_id.get(failure_id)

    def list_open(self) -> list[FailureRecord]:
        return sorted(
            (r for r in self._by_id.values() if r.status == "open"),
            key=lambda r: r.created_at,
        )


def _to_response(record: FailureRecord) -> FailureResponse:
    return FailureResponse(
        id=record.id,
        case_id=record.case_id,
        patient_id=record.patient_id,
        modality=record.modality,
        error_summary=record.error_summary,
        attempts=record.attempts,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class FailureService:
    def __init__(
        self,
        *,
        store: FailureStore,
        case_store: CaseStore,
        outbox_dispatcher: OutboxDispatcher,
        audit_store: AuditStore | None = None,
    ) -> None:
        self._store = store
        self._case_store = case_store
        self._outbox = outbox_dispatcher
        self._audit_store = audit_store or InMemoryAuditStore()

    def record_failure(
        self,
        *,
        case: CaseRecord,
        modality: str,
        error_summary: str,
        attempts: int | None = None,
    ) -> FailureRecord:
        now = datetime.now(tz=UTC)
        policy_attempts = attempts or RetryPolicy.from_environment().max_attempts
        record = FailureRecord(
            id=uuid.uuid4(),
            case_id=case.id,
            patient_id=case.patient_id,
            modality=modality,
            error_summary=error_summary[:2000],
            attempts=policy_attempts,
            status="open",
            created_at=now,
            updated_at=now,
        )
        return self._store.save(record)

    def list_open(self) -> list[FailureResponse]:
        return [_to_response(r) for r in self._store.list_open()]

    def get(self, failure_id: uuid.UUID) -> FailureResponse:
        record = self._store.get(failure_id)
        if record is None:
            raise FailureNotFoundError()
        return _to_response(record)

    def redrive(
        self, failure_id: uuid.UUID, *, operator_id: uuid.UUID
    ) -> FailureResponse:
        record = self._store.get(failure_id)
        if record is None:
            raise FailureNotFoundError()
        if record.status != "open":
            raise FailureNotOpenError()

        case = self._case_store.get(record.case_id)
        if case is None:
            raise FailureNotFoundError()

        now = datetime.now(tz=UTC)
        updated_modalities = [
            ModalityRecord(
                id=m.id,
                case_id=m.case_id,
                modality=m.modality,
                status="pending" if m.modality == record.modality else m.status,
                artifact_id=m.artifact_id,
                created_at=m.created_at,
                updated_at=now if m.modality == record.modality else m.updated_at,
            )
            for m in case.modalities
        ]
        updated_case = CaseRecord(
            id=case.id,
            patient_id=case.patient_id,
            status="processing",
            risk_score=case.risk_score,
            risk_level=case.risk_level,
            idempotency_key=case.idempotency_key,
            content_sha256=case.content_sha256,
            created_at=case.created_at,
            updated_at=now,
            modalities=updated_modalities,
            artifacts=case.artifacts,
            alerts=case.alerts,
            video_idempotency_key=case.video_idempotency_key,
            video_content_sha256=case.video_content_sha256,
            audio_idempotency_key=case.audio_idempotency_key,
            audio_content_sha256=case.audio_content_sha256,
        )
        self._case_store.save(updated_case)

        job = self._outbox.create_pending(
            aggregate_type="case",
            aggregate_id=case.id,
            job_type="process_modality",
            payload={"case_id": str(case.id), "modality": record.modality},
        )
        self._outbox.try_enqueue(job.id)

        redriven = FailureRecord(
            id=record.id,
            case_id=record.case_id,
            patient_id=record.patient_id,
            modality=record.modality,
            error_summary=record.error_summary,
            attempts=record.attempts,
            status="redriven",
            created_at=record.created_at,
            updated_at=now,
        )
        saved = self._store.save(redriven)
        self._audit_store.append(
            AuditRecord(
                id=uuid.uuid4(),
                operator_id=operator_id,
                patient_id=record.patient_id,
                action=DLQ_REDRIVE,
                created_at=now,
            )
        )
        return _to_response(saved)

    def discard(
        self, failure_id: uuid.UUID, *, operator_id: uuid.UUID
    ) -> FailureResponse:
        record = self._store.get(failure_id)
        if record is None:
            raise FailureNotFoundError()
        if record.status != "open":
            raise FailureNotOpenError()

        now = datetime.now(tz=UTC)
        discarded = FailureRecord(
            id=record.id,
            case_id=record.case_id,
            patient_id=record.patient_id,
            modality=record.modality,
            error_summary=record.error_summary,
            attempts=record.attempts,
            status="discarded",
            created_at=record.created_at,
            updated_at=now,
        )
        saved = self._store.save(discarded)
        self._audit_store.append(
            AuditRecord(
                id=uuid.uuid4(),
                operator_id=operator_id,
                patient_id=record.patient_id,
                action=DLQ_DISCARD,
                created_at=now,
            )
        )
        return _to_response(saved)


_default_failure_store = InMemoryFailureStore()
_default_audit_store = InMemoryAuditStore()
_failure_recorder: FailureService | None = None


def configure_failure_recorder(service: FailureService | None) -> None:
    """Permite ao worker/API registrar falhas no mesmo store da DLQ."""
    global _failure_recorder
    _failure_recorder = service


def get_failure_recorder() -> FailureService | None:
    if _failure_recorder is not None:
        return _failure_recorder
    from app.cases.runtime import uses_shared_postgres_store

    # Worker RQ no Compose: monta recorder SQL sob demanda (como CaseRuntime).
    if uses_shared_postgres_store():
        return get_failure_service()
    return None


def record_processing_failure(
    *,
    case: CaseRecord,
    modality: str,
    error_summary: str,
    attempts: int | None = None,
) -> None:
    """Best-effort: registra na DLQ se o recorder estiver configurado."""
    recorder = get_failure_recorder()
    if recorder is None:
        return
    recorder.record_failure(
        case=case,
        modality=modality,
        error_summary=error_summary,
        attempts=attempts,
    )


def get_failure_service() -> FailureService:
    from app.cases.runtime import uses_shared_postgres_store
    from app.cases.service import _default_case_store, _default_dispatcher
    from app.patients.service import _default_audit_store as patient_audit

    if uses_shared_postgres_store():
        from app.cases.db_store import SqlAlchemyCaseStore
        from app.failures.db_store import SqlAlchemyFailureStore
        from app.outbox.db_store import SqlAlchemyOutboxStore
        from app.outbox.rq_client import RqJobEnqueuer
        from app.outbox.service import OutboxDispatcher as OD

        service = FailureService(
            store=SqlAlchemyFailureStore(),
            case_store=SqlAlchemyCaseStore(),
            outbox_dispatcher=OD(
                store=SqlAlchemyOutboxStore(), enqueuer=RqJobEnqueuer()
            ),
            audit_store=patient_audit,
        )
        configure_failure_recorder(service)
        return service

    service = FailureService(
        store=_default_failure_store,
        case_store=_default_case_store,
        outbox_dispatcher=_default_dispatcher(),
        audit_store=_default_audit_store,
    )
    configure_failure_recorder(service)
    return service
