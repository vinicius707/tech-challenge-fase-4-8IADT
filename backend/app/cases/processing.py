"""Pipeline assíncrono: vitais → AnomalyEngine → Fusion → Risco no Caso."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.cases.runtime import CaseRuntime, get_case_runtime
from app.cases.service import CaseRecord, ModalityRecord
from app.cases.vitals_engine import VitalsAnomalyEngine, fuse_vitals_only


def process_vitals_for_case(
    case_id: uuid.UUID,
    *,
    runtime: CaseRuntime | None = None,
    engine: VitalsAnomalyEngine | None = None,
) -> CaseRecord | None:
    """Atualiza o Caso com Risco. No-op se modalidade vitais já estiver `done`."""
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
    )
    return ctx.case_store.save(done)
