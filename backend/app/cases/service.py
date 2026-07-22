"""Serviço de Caso — criação idempotente com Artefato (MinIO) e outbox."""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.cases.schemas import (
    AlertResponse,
    ArtifactResponse,
    CaseResponse,
    ModalityResponse,
)
from app.cases.storage import (
    ArtifactBlobStore,
    InMemoryArtifactBlobStore,
    MinioArtifactBlobStore,
)
from app.outbox.service import OutboxDispatcher
from app.patients.service import PatientStore


class PatientNotFoundError(Exception):
    pass


class CaseNotFoundError(Exception):
    pass


class IdempotencyConflictError(Exception):
    pass


@dataclass
class ArtifactRecord:
    id: uuid.UUID
    case_id: uuid.UUID
    modality: str
    bucket: str
    object_key: str
    content_sha256: str
    content_type: str
    created_at: datetime


@dataclass
class ModalityRecord:
    id: uuid.UUID
    case_id: uuid.UUID
    modality: str
    status: str
    artifact_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


@dataclass
class AlertRecord:
    id: uuid.UUID
    case_id: uuid.UUID
    level: str
    version: int
    created_at: datetime


@dataclass
class CaseRecord:
    id: uuid.UUID
    patient_id: uuid.UUID
    status: str
    risk_score: float | None
    risk_level: str | None
    idempotency_key: str | None
    content_sha256: str | None
    created_at: datetime
    updated_at: datetime
    modalities: list[ModalityRecord] = field(default_factory=list)
    artifacts: list[ArtifactRecord] = field(default_factory=list)
    alerts: list[AlertRecord] = field(default_factory=list)


class CaseStore(Protocol):
    def save(self, case: CaseRecord) -> CaseRecord: ...

    def get(self, case_id: uuid.UUID) -> CaseRecord | None: ...

    def get_by_idempotency_key(self, key: str) -> CaseRecord | None: ...

    def delete_by_patient(self, patient_id: uuid.UUID) -> int: ...


@dataclass
class InMemoryCaseStore:
    _by_id: dict[uuid.UUID, CaseRecord] = field(default_factory=dict)
    _by_idempotency: dict[str, uuid.UUID] = field(default_factory=dict)

    def save(self, case: CaseRecord) -> CaseRecord:
        self._by_id[case.id] = case
        if case.idempotency_key:
            self._by_idempotency[case.idempotency_key] = case.id
        return case

    def get(self, case_id: uuid.UUID) -> CaseRecord | None:
        return self._by_id.get(case_id)

    def get_by_idempotency_key(self, key: str) -> CaseRecord | None:
        case_id = self._by_idempotency.get(key)
        if case_id is None:
            return None
        return self._by_id.get(case_id)

    def delete_by_patient(self, patient_id: uuid.UUID) -> int:
        to_remove = [
            case_id
            for case_id, record in self._by_id.items()
            if record.patient_id == patient_id
        ]
        for case_id in to_remove:
            record = self._by_id.pop(case_id)
            if record.idempotency_key:
                self._by_idempotency.pop(record.idempotency_key, None)
        return len(to_remove)


def _to_response(case: CaseRecord) -> CaseResponse:
    return CaseResponse(
        id=case.id,
        patient_id=case.patient_id,
        status=case.status,
        risk_score=case.risk_score,
        risk_level=case.risk_level,
        modalities=[
            ModalityResponse(
                modality=m.modality,
                status=m.status,
                artifact_id=m.artifact_id,
            )
            for m in case.modalities
        ],
        artifacts=[
            ArtifactResponse(
                id=a.id,
                modality=a.modality,
                bucket=a.bucket,
                object_key=a.object_key,
                content_sha256=a.content_sha256,
                content_type=a.content_type,
            )
            for a in case.artifacts
        ],
        alerts=[
            AlertResponse(
                id=a.id,
                case_id=a.case_id,
                level=a.level,
                version=a.version,
                created_at=a.created_at,
            )
            for a in case.alerts
        ],
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


class CaseService:
    def __init__(
        self,
        *,
        store: CaseStore,
        patient_store: PatientStore,
        blob_store: ArtifactBlobStore,
        outbox_dispatcher: OutboxDispatcher,
        default_bucket: str | None = None,
    ) -> None:
        self._store = store
        self._patient_store = patient_store
        self._blobs = blob_store
        self._outbox = outbox_dispatcher
        self._bucket = default_bucket or os.getenv("MINIO_BUCKET", "limen")

    def create(
        self,
        *,
        patient_id: uuid.UUID,
        idempotency_key: str,
        content: bytes,
        content_type: str = "text/csv",
        filename: str = "vitals.csv",
    ) -> tuple[CaseResponse, bool]:
        """Retorna (resposta, created). created=False em replay idempotente."""
        if self._patient_store.get_by_id(patient_id) is None:
            raise PatientNotFoundError()

        digest = hashlib.sha256(content).hexdigest()
        existing = self._store.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            if existing.content_sha256 == digest:
                return _to_response(existing), False
            raise IdempotencyConflictError()

        now = datetime.now(tz=UTC)
        case_id = uuid.uuid4()
        artifact_id = uuid.uuid4()
        object_key = f"cases/{case_id}/vitals/{filename}"

        self._blobs.put(
            bucket=self._bucket,
            object_key=object_key,
            content=content,
            content_type=content_type,
        )

        artifact = ArtifactRecord(
            id=artifact_id,
            case_id=case_id,
            modality="vitals",
            bucket=self._bucket,
            object_key=object_key,
            content_sha256=digest,
            content_type=content_type,
            created_at=now,
        )
        modality = ModalityRecord(
            id=uuid.uuid4(),
            case_id=case_id,
            modality="vitals",
            status="pending",
            artifact_id=artifact_id,
            created_at=now,
            updated_at=now,
        )
        case = CaseRecord(
            id=case_id,
            patient_id=patient_id,
            status="pending",
            risk_score=None,
            risk_level=None,
            idempotency_key=idempotency_key,
            content_sha256=digest,
            created_at=now,
            updated_at=now,
            modalities=[modality],
            artifacts=[artifact],
        )
        self._store.save(case)

        outbox_job = self._outbox.create_pending(
            aggregate_type="case",
            aggregate_id=case_id,
            job_type="process_modality",
            payload={"case_id": str(case_id), "modality": "vitals"},
        )
        self._outbox.try_enqueue(outbox_job.id)

        return _to_response(case), True

    def get(self, case_id: uuid.UUID) -> CaseResponse:
        case = self._store.get(case_id)
        if case is None:
            raise CaseNotFoundError()
        return _to_response(case)


_default_case_store = InMemoryCaseStore()
_default_blob_store: ArtifactBlobStore = InMemoryArtifactBlobStore()
_default_outbox_dispatcher: OutboxDispatcher | None = None
_shared_outbox_dispatcher: OutboxDispatcher | None = None


def _default_dispatcher() -> OutboxDispatcher:
    global _default_outbox_dispatcher
    if _default_outbox_dispatcher is None:
        from app.outbox.rq_client import RqJobEnqueuer
        from app.outbox.service import InMemoryOutboxStore

        # Testes/dev sem Compose: memória. Compose usa `_shared_dispatcher`.
        _default_outbox_dispatcher = OutboxDispatcher(
            store=InMemoryOutboxStore(),
            enqueuer=RqJobEnqueuer(),
        )
    return _default_outbox_dispatcher


def _shared_dispatcher() -> OutboxDispatcher:
    """Outbox no Postgres compartilhado com o worker (Compose)."""
    global _shared_outbox_dispatcher
    if _shared_outbox_dispatcher is None:
        from app.outbox.db_store import SqlAlchemyOutboxStore
        from app.outbox.rq_client import RqJobEnqueuer

        _shared_outbox_dispatcher = OutboxDispatcher(
            store=SqlAlchemyOutboxStore(),
            enqueuer=RqJobEnqueuer(),
        )
    return _shared_outbox_dispatcher


def get_case_service() -> CaseService:
    from app.cases.runtime import uses_shared_postgres_store
    from app.patients.db_store import SqlAlchemyPatientStore
    from app.patients.service import _default_store as default_patient_store

    if uses_shared_postgres_store():
        from app.cases.db_store import SqlAlchemyCaseStore

        return CaseService(
            store=SqlAlchemyCaseStore(),
            patient_store=SqlAlchemyPatientStore(),
            blob_store=MinioArtifactBlobStore(),
            outbox_dispatcher=_shared_dispatcher(),
        )

    return CaseService(
        store=_default_case_store,
        patient_store=default_patient_store,
        blob_store=_default_blob_store,
        outbox_dispatcher=_default_dispatcher(),
    )
