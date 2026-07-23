"""Store Postgres para Caso / modalidades / Artefatos / Alertas (API↔worker)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.cases.models import Alert, Artifact, Case, CaseModality
from app.cases.service import (
    AlertRecord,
    ArtifactRecord,
    CaseRecord,
    ModalityRecord,
)
from app.db import get_session_factory


def _to_record(
    case_row: Case,
    modalities: list[CaseModality],
    artifacts: list[Artifact],
    alerts: list[Alert],
) -> CaseRecord:
    return CaseRecord(
        id=case_row.id,
        patient_id=case_row.patient_id,
        status=case_row.status,
        risk_score=case_row.risk_score,
        risk_level=case_row.risk_level,
        justification=case_row.justification,
        idempotency_key=case_row.idempotency_key,
        content_sha256=case_row.content_sha256,
        created_at=case_row.created_at,
        updated_at=case_row.updated_at,
        video_idempotency_key=case_row.video_idempotency_key,
        video_content_sha256=case_row.video_content_sha256,
        audio_idempotency_key=case_row.audio_idempotency_key,
        audio_content_sha256=case_row.audio_content_sha256,
        prescriptions_idempotency_key=case_row.prescriptions_idempotency_key,
        prescriptions_content_sha256=case_row.prescriptions_content_sha256,
        modalities=[
            ModalityRecord(
                id=m.id,
                case_id=m.case_id,
                modality=m.modality,
                status=m.status,
                artifact_id=m.artifact_id,
                created_at=m.created_at,
                updated_at=m.updated_at,
                provider=m.provider,
            )
            for m in modalities
        ],
        artifacts=[
            ArtifactRecord(
                id=a.id,
                case_id=a.case_id,
                modality=a.modality,
                bucket=a.bucket,
                object_key=a.object_key,
                content_sha256=a.content_sha256,
                content_type=a.content_type,
                created_at=a.created_at,
            )
            for a in artifacts
        ],
        alerts=[
            AlertRecord(
                id=al.id,
                case_id=al.case_id,
                level=al.level,
                version=al.version,
                created_at=al.created_at,
            )
            for al in alerts
        ],
    )


class SqlAlchemyCaseStore:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def save(self, case: CaseRecord) -> CaseRecord:
        with self._session_factory() as session:
            row = session.get(Case, case.id)
            if row is None:
                row = Case(id=case.id, created_at=case.created_at)
                session.add(row)
            row.patient_id = case.patient_id
            row.status = case.status
            row.risk_score = case.risk_score
            row.risk_level = case.risk_level
            row.justification = case.justification
            row.idempotency_key = case.idempotency_key
            row.content_sha256 = case.content_sha256
            row.video_idempotency_key = case.video_idempotency_key
            row.video_content_sha256 = case.video_content_sha256
            row.audio_idempotency_key = case.audio_idempotency_key
            row.audio_content_sha256 = case.audio_content_sha256
            row.prescriptions_idempotency_key = case.prescriptions_idempotency_key
            row.prescriptions_content_sha256 = case.prescriptions_content_sha256
            row.updated_at = case.updated_at or datetime.now(tz=UTC)

            self._sync_artifacts(session, case)
            session.flush()
            self._sync_modalities(session, case)
            self._sync_alerts(session, case)
            session.commit()
            return self._load(session, case.id)

    def get(self, case_id: uuid.UUID) -> CaseRecord | None:
        with self._session_factory() as session:
            row = session.get(Case, case_id)
            if row is None:
                return None
            return self._load(session, case_id)

    def get_by_idempotency_key(self, key: str) -> CaseRecord | None:
        with self._session_factory() as session:
            row = session.scalars(
                select(Case).where(Case.idempotency_key == key)
            ).first()
            if row is None:
                return None
            return self._load(session, row.id)

    def get_by_video_idempotency_key(self, key: str) -> CaseRecord | None:
        with self._session_factory() as session:
            row = session.scalars(
                select(Case).where(Case.video_idempotency_key == key)
            ).first()
            if row is None:
                return None
            return self._load(session, row.id)

    def get_by_audio_idempotency_key(self, key: str) -> CaseRecord | None:
        with self._session_factory() as session:
            row = session.scalars(
                select(Case).where(Case.audio_idempotency_key == key)
            ).first()
            if row is None:
                return None
            return self._load(session, row.id)

    def get_by_prescriptions_idempotency_key(self, key: str) -> CaseRecord | None:
        with self._session_factory() as session:
            row = session.scalars(
                select(Case).where(Case.prescriptions_idempotency_key == key)
            ).first()
            if row is None:
                return None
            return self._load(session, row.id)

    def list_by_patient(self, patient_id: uuid.UUID) -> list[CaseRecord]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(Case)
                .where(Case.patient_id == patient_id)
                .order_by(Case.created_at.asc())
            ).all()
            return [self._load(session, row.id) for row in rows]

    def delete_by_patient(self, patient_id: uuid.UUID) -> int:
        with self._session_factory() as session:
            rows = session.scalars(
                select(Case).where(Case.patient_id == patient_id)
            ).all()
            count = len(rows)
            for row in rows:
                session.delete(row)
            session.commit()
            return count

    def _load(self, session: Session, case_id: uuid.UUID) -> CaseRecord:
        case_row = session.get(Case, case_id)
        assert case_row is not None
        modalities = list(
            session.scalars(
                select(CaseModality)
                .where(CaseModality.case_id == case_id)
                .order_by(CaseModality.created_at.asc())
            ).all()
        )
        artifacts = list(
            session.scalars(
                select(Artifact)
                .where(Artifact.case_id == case_id)
                .order_by(Artifact.created_at.asc())
            ).all()
        )
        alerts = list(
            session.scalars(
                select(Alert)
                .where(Alert.case_id == case_id)
                .order_by(Alert.version.asc(), Alert.created_at.asc())
            ).all()
        )
        return _to_record(case_row, modalities, artifacts, alerts)

    def _sync_artifacts(self, session: Session, case: CaseRecord) -> None:
        existing = {
            row.id: row
            for row in session.scalars(
                select(Artifact).where(Artifact.case_id == case.id)
            ).all()
        }
        keep = {a.id for a in case.artifacts}
        for art_id, row in existing.items():
            if art_id not in keep:
                session.delete(row)
        for art in case.artifacts:
            row = existing.get(art.id)
            if row is None:
                row = Artifact(id=art.id, created_at=art.created_at)
                session.add(row)
            row.case_id = case.id
            row.modality = art.modality
            row.bucket = art.bucket
            row.object_key = art.object_key
            row.content_sha256 = art.content_sha256
            row.content_type = art.content_type

    def _sync_modalities(self, session: Session, case: CaseRecord) -> None:
        existing = {
            row.id: row
            for row in session.scalars(
                select(CaseModality).where(CaseModality.case_id == case.id)
            ).all()
        }
        keep = {m.id for m in case.modalities}
        for mod_id, row in existing.items():
            if mod_id not in keep:
                session.delete(row)
        for mod in case.modalities:
            row = existing.get(mod.id)
            if row is None:
                row = CaseModality(id=mod.id, created_at=mod.created_at)
                session.add(row)
            row.case_id = case.id
            row.modality = mod.modality
            row.status = mod.status
            row.provider = mod.provider
            row.artifact_id = mod.artifact_id
            row.updated_at = mod.updated_at

    def _sync_alerts(self, session: Session, case: CaseRecord) -> None:
        existing = {
            row.id: row
            for row in session.scalars(
                select(Alert).where(Alert.case_id == case.id)
            ).all()
        }
        keep = {a.id for a in case.alerts}
        for alert_id, row in existing.items():
            if alert_id not in keep:
                session.delete(row)
        for alert in case.alerts:
            row = existing.get(alert.id)
            if row is None:
                row = Alert(id=alert.id, created_at=alert.created_at)
                session.add(row)
            row.case_id = case.id
            row.level = alert.level
            row.version = alert.version
