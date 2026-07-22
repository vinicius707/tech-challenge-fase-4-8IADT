"""Pipeline assíncrono: modalidades → Fusion → Risco → Alertas versionados."""

from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime

from app.cases.runtime import CaseRuntime, get_case_runtime
from app.cases.service import AlertRecord, CaseRecord, ModalityRecord
from app.cases.vitals_engine import (
    ModalityRisk,
    VitalsAnomalyEngine,
    fuse_done_modalities,
)
from app.failures.service import record_processing_failure
from app.outbox.retries import PermanentProcessingError, TransientProcessingError
from app.outbox.timeouts import ModalityTimeoutError, run_with_modality_timeout

ALERT_VERSION_V1 = 1
FORCE_FAIL_ENV = "LIMEN_FORCE_FAIL_MODALITIES"
FORCE_SLOW_ENV = "LIMEN_FORCE_SLOW_MODALITIES"
FORCE_PERMANENT_ENV = "LIMEN_FORCE_PERMANENT_FAIL_MODALITIES"
FORCE_TRANSIENT_ENV = "LIMEN_FORCE_TRANSIENT_FAIL_MODALITIES"
TERMINAL_STATUSES = frozenset({"done", "failed", "skipped"})
STUB_SUCCESS_RISK = ModalityRisk(score=0.10, level="BAIXO", anomalies=())
ALERT_WORTHY_LEVELS = frozenset({"MEDIO", "ALTO"})


def _alerts_after_fusion(
    case: CaseRecord,
    risk_level: str,
    *,
    now: datetime,
) -> list[AlertRecord]:
    """Append-only: v1 se ≥ MEDIO; nova versão se o risk_level mudar após reprocess."""
    alerts = list(case.alerts)
    previous_level = case.risk_level

    if not alerts:
        if risk_level not in ALERT_WORTHY_LEVELS:
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

    if previous_level == risk_level:
        return alerts

    next_version = max(a.version for a in alerts) + 1
    if any(a.level == risk_level and a.version == next_version for a in alerts):
        return alerts
    alerts.append(
        AlertRecord(
            id=uuid.uuid4(),
            case_id=case.id,
            level=risk_level,
            version=next_version,
            created_at=now,
        )
    )
    return alerts


def _forced_fail_modalities() -> set[str]:
    raw = os.getenv(FORCE_FAIL_ENV, "")
    return {part.strip() for part in raw.split(",") if part.strip()}


def _csv_env_modalities(env_name: str) -> set[str]:
    raw = os.getenv(env_name, "")
    return {part.strip() for part in raw.split(",") if part.strip()}


def _maybe_inject_test_hooks(modality: str) -> None:
    """Hooks só para TDD/demo — não usam rede."""
    if modality in _csv_env_modalities(FORCE_TRANSIENT_ENV):
        raise TransientProcessingError(f"falha transitória forçada: {modality}")
    if modality in _csv_env_modalities(FORCE_PERMANENT_ENV):
        raise PermanentProcessingError(f"falha permanente forçada: {modality}")
    if modality in _csv_env_modalities(FORCE_SLOW_ENV):
        delay = float(os.getenv("LIMEN_FORCE_SLOW_SECONDS", "5"))
        time.sleep(delay)


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
        video_idempotency_key=case.video_idempotency_key,
        video_content_sha256=case.video_content_sha256,
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
            video_idempotency_key=case.video_idempotency_key,
            video_content_sha256=case.video_content_sha256,
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
            video_idempotency_key=case.video_idempotency_key,
            video_content_sha256=case.video_content_sha256,
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
        video_idempotency_key=case.video_idempotency_key,
        video_content_sha256=case.video_content_sha256,
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
        video_idempotency_key=case.video_idempotency_key,
        video_content_sha256=case.video_content_sha256,
    )
    ctx.case_store.save(case)

    fail_reason: str | None = None

    def _work() -> CaseRecord:
        nonlocal fail_reason
        _maybe_inject_test_hooks(modality)
        force_fail = modality in _forced_fail_modalities()
        current = case
        if force_fail:
            fail_reason = f"falha forçada: {modality}"
            return _replace_modality_status(current, modality, "failed", now=now)
        if modality == "vitals":
            artifact = next(
                (a for a in current.artifacts if a.modality == "vitals"), None
            )
            if artifact is None:
                fail_reason = "artefato de vitais ausente"
                return _replace_modality_status(current, modality, "failed", now=now)
            content = ctx.blob_store.get(artifact.bucket, artifact.object_key)
            if content is None:
                raise PermanentProcessingError(
                    f"Artefato ausente: {artifact.bucket}/{artifact.object_key}"
                )
            analyzer.analyze_csv(content)
            return _replace_modality_status(current, modality, "done", now=now)
        if modality == "audio":
            return _replace_modality_status(current, modality, "done", now=now)
        fail_reason = f"modalidade sem handler: {modality}"
        return _replace_modality_status(current, modality, "failed", now=now)

    try:
        case = run_with_modality_timeout(modality, _work)
    except ModalityTimeoutError as exc:
        fail_reason = str(exc) or f"timeout: {modality}"
        case = _replace_modality_status(case, modality, "failed", now=now)
    except PermanentProcessingError as exc:
        fail_reason = str(exc) or f"erro permanente: {modality}"
        case = _replace_modality_status(case, modality, "failed", now=now)
    except TransientProcessingError:
        # Deixa em `processing` para o RQ retentar (ADR 0015).
        raise

    if fail_reason is not None or any(
        m.modality == modality and m.status == "failed" for m in case.modalities
    ):
        record_processing_failure(
            case=case,
            modality=modality,
            error_summary=fail_reason or f"falha de processamento: {modality}",
        )

    finalized = _finalize_case(case, runtime=ctx, engine=analyzer, now=now)
    return ctx.case_store.save(finalized)
