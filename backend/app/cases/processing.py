"""Pipeline assíncrono: vitais → AnomalyEngine → Fusion → Risco → Alerta v1."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.cases.runtime import CaseRuntime, get_case_runtime
from app.cases.service import AlertRecord, CaseRecord, ModalityRecord
from app.cases.vitals_engine import VitalsAnomalyEngine, fuse_vitals_only

ALERT_VERSION_V1 = 1


def _alerts_after_fusion(
    case: CaseRecord,
    risk_level: str,
    *,
    now: datetime,
) -> list[AlertRecord]:
    """Emite Alerta v1 se ≥ MEDIO; dedupe por (case_id, level, version)."""
    alerts = list(case.alerts)
    if risk_level not in {"MEDIO", "ALTO"}:
        return alerts
    if any(
        a.level == risk_level and a.version == ALERT_VERSION_V1 for a in alerts
    ):
        return alerts
    alerts.append(
        AlertRecord(
            id=uuid.uuid4(),
            case_id=case.id,
            level=risk_level,
            version=ALERT_VERSION_V1,
            created_at=now,
        )
    )
    return alerts


def process_vitals_for_case(
    case_id: uuid.UUID,
    *,
    runtime: CaseRuntime | None = None,
    engine: VitalsAnomalyEngine | None = None,
) -> CaseRecord | None:
    """Atualiza o Caso com Risco e Alerta v1. No-op se modalidade já `done`."""
    ctx = runtime or get_case_runtime()
    if ctx is None:
        return None

    case = ctx.case_store.get(case_id)
    if case is None:
        return None

    vitals_mod = next((m for m in case.modalities if m.modality == "vitals"), None)
    if vitals_mod is None:
        return case
    if vitals_mod.status == "done" and case.status == "done":
        return case

    artifact = next((a for a in case.artifacts if a.modality == "vitals"), None)
    if artifact is None:
        return case

    content = ctx.blob_store.get(artifact.bucket, artifact.object_key)
    if content is None:
        raise FileNotFoundError(
            f"Artefato ausente: {artifact.bucket}/{artifact.object_key}"
        )

    now = datetime.now(tz=UTC)
    processing_mods = [
        ModalityRecord(
            id=m.id,
            case_id=m.case_id,
            modality=m.modality,
            status="processing" if m.modality == "vitals" else m.status,
            artifact_id=m.artifact_id,
            created_at=m.created_at,
            updated_at=now if m.modality == "vitals" else m.updated_at,
        )
        for m in case.modalities
    ]
    case = CaseRecord(
        id=case.id,
        patient_id=case.patient_id,
        status="processing",
        risk_score=case.risk_score,
        risk_level=case.risk_level,
        idempotency_key=case.idempotency_key,
        content_sha256=case.content_sha256,
        created_at=case.created_at,
        updated_at=now,
        modalities=processing_mods,
        artifacts=case.artifacts,
        alerts=case.alerts,
    )
    ctx.case_store.save(case)

    analyzer = engine or VitalsAnomalyEngine()
    vitals_risk = analyzer.analyze_csv(content)
    fused = fuse_vitals_only(vitals_risk)

    done_mods = [
        ModalityRecord(
            id=m.id,
            case_id=m.case_id,
            modality=m.modality,
            status="done" if m.modality == "vitals" else m.status,
            artifact_id=m.artifact_id,
            created_at=m.created_at,
            updated_at=now if m.modality == "vitals" else m.updated_at,
        )
        for m in case.modalities
    ]
    done = CaseRecord(
        id=case.id,
        patient_id=case.patient_id,
        status="done",
        risk_score=fused.score,
        risk_level=fused.level,
        idempotency_key=case.idempotency_key,
        content_sha256=case.content_sha256,
        created_at=case.created_at,
        updated_at=now,
        modalities=done_mods,
        artifacts=case.artifacts,
        alerts=_alerts_after_fusion(case, fused.level, now=now),
    )
    return ctx.case_store.save(done)
