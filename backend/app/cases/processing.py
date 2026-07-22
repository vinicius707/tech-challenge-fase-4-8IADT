"""Pipeline assíncrono: modalidades → Fusion → Risco → Alerta v1 (falha parcial)."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

from app.cases.runtime import CaseRuntime, get_case_runtime
from app.cases.service import AlertRecord, CaseRecord, ModalityRecord
from app.cases.vitals_engine import (
    ModalityRisk,
    VitalsAnomalyEngine,
    fuse_done_modalities,
)

ALERT_VERSION_V1 = 1
FORCE_FAIL_ENV = "LIMEN_FORCE_FAIL_MODALITIES"
TERMINAL_STATUSES = frozenset({"done", "failed", "skipped"})
STUB_SUCCESS_RISK = ModalityRisk(score=0.10, level="BAIXO", anomalies=())


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


def _forced_fail_modalities() -> set[str]:
    raw = os.getenv(FORCE_FAIL_ENV, "")
    return {part.strip() for part in raw.split(",") if part.strip()}


def _replace_modality_status(
    case: CaseRecord,
    modality: str,
    status: str,
    *,
    now: datetime,
) -> CaseRecord:
    modalities = [
        ModalityRecord(
            id=m.id,
            case_id=m.case_id,
            modality=m.modality,
            status=status if m.modality == modality else m.status,
            artifact_id=m.artifact_id,
            created_at=m.created_at,
            updated_at=now if m.modality == modality else m.updated_at,
        )
        for m in case.modalities
    ]
    return CaseRecord(
        id=case.id,
        patient_id=case.patient_id,
        status=case.status,
        risk_score=case.risk_score,
        risk_level=case.risk_level,
        idempotency_key=case.idempotency_key,
        content_sha256=case.content_sha256,
        created_at=case.created_at,
        updated_at=now,
        modalities=modalities,
        artifacts=case.artifacts,
        alerts=case.alerts,
    )


def _all_terminal(case: CaseRecord) -> bool:
    return bool(case.modalities) and all(
        m.status in TERMINAL_STATUSES for m in case.modalities
    )


def _risk_for_done_modality(
    case: CaseRecord,
    modality: str,
    *,
    runtime: CaseRuntime,
    engine: VitalsAnomalyEngine,
) -> ModalityRisk | None:
    if modality == "vitals":
        artifact = next((a for a in case.artifacts if a.modality == "vitals"), None)
        if artifact is None:
            return None
        content = runtime.blob_store.get(artifact.bucket, artifact.object_key)
        if content is None:
            raise FileNotFoundError(
                f"Artefato ausente: {artifact.bucket}/{artifact.object_key}"
            )
        return engine.analyze_csv(content)
    if modality == "audio":
        return STUB_SUCCESS_RISK
    return None


def _finalize_case(
    case: CaseRecord,
    *,
    runtime: CaseRuntime,
    engine: VitalsAnomalyEngine,
    now: datetime,
) -> CaseRecord:
    """Fecha o Caso quando todas as modalidades são terminais (falha parcial OK)."""
    if not _all_terminal(case):
        return CaseRecord(
            id=case.id,
            patient_id=case.patient_id,
            status="processing",
            risk_score=case.risk_score,
            risk_level=case.risk_level,
            idempotency_key=case.idempotency_key,
            content_sha256=case.content_sha256,
            created_at=case.created_at,
            updated_at=now,
            modalities=case.modalities,
            artifacts=case.artifacts,
            alerts=case.alerts,
        )

    done_names = [m.modality for m in case.modalities if m.status == "done"]
    if not done_names:
        return CaseRecord(
            id=case.id,
            patient_id=case.patient_id,
            status="failed",
            risk_score=None,
            risk_level=None,
            idempotency_key=case.idempotency_key,
            content_sha256=case.content_sha256,
            created_at=case.created_at,
            updated_at=now,
            modalities=case.modalities,
            artifacts=case.artifacts,
            alerts=case.alerts,
        )

    risks: list[ModalityRisk] = []
    for name in done_names:
        risk = _risk_for_done_modality(
            case, name, runtime=runtime, engine=engine
        )
        if risk is not None:
            risks.append(risk)
    fused = fuse_done_modalities(risks)
    return CaseRecord(
        id=case.id,
        patient_id=case.patient_id,
        status="done",
        risk_score=fused.score,
        risk_level=fused.level,
        idempotency_key=case.idempotency_key,
        content_sha256=case.content_sha256,
        created_at=case.created_at,
        updated_at=now,
        modalities=case.modalities,
        artifacts=case.artifacts,
        alerts=_alerts_after_fusion(case, fused.level, now=now),
    )


def process_vitals_for_case(
    case_id: uuid.UUID,
    *,
    runtime: CaseRuntime | None = None,
    engine: VitalsAnomalyEngine | None = None,
) -> CaseRecord | None:
    """Processa vitais; Caso só fecha quando todas as modalidades forem terminais."""
    return process_modality_for_case(
        case_id,
        "vitals",
        runtime=runtime,
        engine=engine,
    )


def process_modality_for_case(
    case_id: uuid.UUID,
    modality: str,
    *,
    runtime: CaseRuntime | None = None,
    engine: VitalsAnomalyEngine | None = None,
) -> CaseRecord | None:
    """Atualiza uma modalidade (`done`/`failed`) e refundiciona se o Caso puder fechar."""
    ctx = runtime or get_case_runtime()
    if ctx is None:
        return None

    case = ctx.case_store.get(case_id)
    if case is None:
        return None

    mod = next((m for m in case.modalities if m.modality == modality), None)
    if mod is None:
        return case
    if mod.status == "done" and case.status == "done":
        return case
    if mod.status == "failed" and _all_terminal(case):
        return case

    analyzer = engine or VitalsAnomalyEngine()
    now = datetime.now(tz=UTC)

    case = _replace_modality_status(case, modality, "processing", now=now)
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
        modalities=case.modalities,
        artifacts=case.artifacts,
        alerts=case.alerts,
    )
    ctx.case_store.save(case)

    force_fail = modality in _forced_fail_modalities()
    if force_fail:
        case = _replace_modality_status(case, modality, "failed", now=now)
    elif modality == "vitals":
        artifact = next((a for a in case.artifacts if a.modality == "vitals"), None)
        if artifact is None:
            return ctx.case_store.save(
                _finalize_case(
                    _replace_modality_status(case, modality, "failed", now=now),
                    runtime=ctx,
                    engine=analyzer,
                    now=now,
                )
            )
        content = ctx.blob_store.get(artifact.bucket, artifact.object_key)
        if content is None:
            raise FileNotFoundError(
                f"Artefato ausente: {artifact.bucket}/{artifact.object_key}"
            )
        analyzer.analyze_csv(content)  # valida o CSV antes de marcar done
        case = _replace_modality_status(case, modality, "done", now=now)
    elif modality == "audio":
        case = _replace_modality_status(case, modality, "done", now=now)
    else:
        case = _replace_modality_status(case, modality, "failed", now=now)

    finalized = _finalize_case(case, runtime=ctx, engine=analyzer, now=now)
    return ctx.case_store.save(finalized)
