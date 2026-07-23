"""Pipeline assíncrono: modalidades → Fusion → Risco → Alertas versionados."""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from datetime import UTC, datetime

from app.cases.justification import build_justification
from app.cases.runtime import CaseRuntime, get_case_runtime
from app.cases.service import AlertRecord, ArtifactRecord, CaseRecord, ModalityRecord
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
    provider: str | None = None,
    set_provider: bool = False,
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
            provider=(
                provider
                if m.modality == modality and set_provider
                else m.provider
            ),
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
        audio_idempotency_key=case.audio_idempotency_key,
        audio_content_sha256=case.audio_content_sha256,
        prescriptions_idempotency_key=case.prescriptions_idempotency_key,
        prescriptions_content_sha256=case.prescriptions_content_sha256,
        justification=case.justification,
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
        artifact = next((a for a in case.artifacts if a.modality == "audio"), None)
        if artifact is None:
            return None
        content = runtime.blob_store.get(artifact.bucket, artifact.object_key)
        if content is None:
            return None
        from app.azure.provider import analyze_audio
        from app.cases.vitals_engine import risk_level_from_score

        analysis = analyze_audio(content)
        return ModalityRisk(
            score=analysis.score,
            level=risk_level_from_score(analysis.score),
            anomalies=(),
        )
    if modality == "video":
        artifact = next((a for a in case.artifacts if a.modality == "video"), None)
        if artifact is None:
            return None
        content = runtime.blob_store.get(artifact.bucket, artifact.object_key)
        if content is None:
            return None
        from app.cases.pose_engine import PosturePoseEngine, resolve_video_analysis
        from app.cases.scene_engine import SceneDetectionEngine

        kind = resolve_video_analysis(artifact.object_key)
        if kind == "pose":
            return PosturePoseEngine().analyze_avi(content).risk
        if kind == "scene":
            return SceneDetectionEngine().analyze_avi(content).risk
        return None
    if modality == "prescriptions":
        artifact = next(
            (a for a in case.artifacts if a.modality == "prescriptions"), None
        )
        if artifact is None:
            return None
        content = runtime.blob_store.get(artifact.bucket, artifact.object_key)
        if content is None:
            return None
        from app.cases.prescriptions_engine import PrescriptionsAnomalyEngine

        history = _prescription_history_blobs(
            case, runtime=runtime
        )
        return PrescriptionsAnomalyEngine().analyze_csv(content, history=history)
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
            audio_idempotency_key=case.audio_idempotency_key,
            audio_content_sha256=case.audio_content_sha256,
            prescriptions_idempotency_key=case.prescriptions_idempotency_key,
            prescriptions_content_sha256=case.prescriptions_content_sha256,
            justification=case.justification,
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
            audio_idempotency_key=case.audio_idempotency_key,
            audio_content_sha256=case.audio_content_sha256,
            prescriptions_idempotency_key=case.prescriptions_idempotency_key,
            prescriptions_content_sha256=case.prescriptions_content_sha256,
            justification=None,
        )

    risks: list[ModalityRisk] = []
    risks_by_modality: dict[str, ModalityRisk] = {}
    for name in done_names:
        risk = _risk_for_done_modality(
            case, name, runtime=runtime, engine=engine
        )
        if risk is not None:
            risks.append(risk)
            risks_by_modality[name] = risk
    fused = fuse_done_modalities(risks)
    justification = build_justification(
        modalities=case.modalities,
        risks_by_modality=risks_by_modality,
        fused_score=fused.score,
        fused_level=fused.level,
    )
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
        audio_idempotency_key=case.audio_idempotency_key,
        audio_content_sha256=case.audio_content_sha256,
        prescriptions_idempotency_key=case.prescriptions_idempotency_key,
        prescriptions_content_sha256=case.prescriptions_content_sha256,
        justification=justification,
    )


def _copy_case_meta(
    case: CaseRecord,
    *,
    now: datetime,
    status: str | None = None,
    risk_score: float | None = None,
    risk_level: str | None = None,
    modalities: list[ModalityRecord] | None = None,
    artifacts: list[ArtifactRecord] | None = None,
    alerts: list[AlertRecord] | None = None,
    justification: dict | None = None,
    set_justification: bool = False,
) -> CaseRecord:
    return CaseRecord(
        id=case.id,
        patient_id=case.patient_id,
        status=case.status if status is None else status,
        risk_score=case.risk_score if risk_score is None else risk_score,
        risk_level=case.risk_level if risk_level is None else risk_level,
        idempotency_key=case.idempotency_key,
        content_sha256=case.content_sha256,
        created_at=case.created_at,
        updated_at=now,
        modalities=case.modalities if modalities is None else modalities,
        artifacts=case.artifacts if artifacts is None else artifacts,
        alerts=case.alerts if alerts is None else alerts,
        video_idempotency_key=case.video_idempotency_key,
        video_content_sha256=case.video_content_sha256,
        audio_idempotency_key=case.audio_idempotency_key,
        audio_content_sha256=case.audio_content_sha256,
        prescriptions_idempotency_key=case.prescriptions_idempotency_key,
        prescriptions_content_sha256=case.prescriptions_content_sha256,
        justification=(
            justification if set_justification else case.justification
        ),
    )


def _process_audio_modality(
    case: CaseRecord,
    *,
    runtime: CaseRuntime,
    now: datetime,
) -> CaseRecord:
    from app.azure.provider import analyze_audio

    artifact = next((a for a in case.artifacts if a.modality == "audio"), None)
    if artifact is None:
        return _replace_modality_status(case, "audio", "failed", now=now)

    content = runtime.blob_store.get(artifact.bucket, artifact.object_key)
    if content is None:
        raise PermanentProcessingError(
            f"Artefato ausente: {artifact.bucket}/{artifact.object_key}"
        )

    analysis = analyze_audio(content)
    return _replace_modality_status(
        case,
        "audio",
        "done",
        now=now,
        provider=analysis.provider,
        set_provider=True,
    )


def _prescription_history_blobs(
    case: CaseRecord,
    *,
    runtime: CaseRuntime,
) -> tuple[bytes, ...]:
    """CSVs de prescriptions `done` de Casos anteriores do mesmo Paciente."""
    prior: list[bytes] = []
    for other in runtime.case_store.list_by_patient(case.patient_id):
        if other.id == case.id:
            continue
        rx_mod = next(
            (m for m in other.modalities if m.modality == "prescriptions"), None
        )
        if rx_mod is None or rx_mod.status != "done":
            continue
        artifact = next(
            (a for a in other.artifacts if a.modality == "prescriptions"), None
        )
        if artifact is None:
            continue
        content = runtime.blob_store.get(artifact.bucket, artifact.object_key)
        if content is not None:
            prior.append(content)
    return tuple(prior)


def _process_prescriptions_modality(
    case: CaseRecord,
    *,
    runtime: CaseRuntime,
    now: datetime,
) -> CaseRecord:
    from app.cases.prescriptions_engine import PrescriptionsAnomalyEngine

    artifact = next(
        (a for a in case.artifacts if a.modality == "prescriptions"), None
    )
    if artifact is None:
        return _replace_modality_status(case, "prescriptions", "failed", now=now)

    content = runtime.blob_store.get(artifact.bucket, artifact.object_key)
    if content is None:
        raise PermanentProcessingError(
            f"Artefato ausente: {artifact.bucket}/{artifact.object_key}"
        )

    history = _prescription_history_blobs(case, runtime=runtime)
    PrescriptionsAnomalyEngine().analyze_csv(content, history=history)
    return _replace_modality_status(case, "prescriptions", "done", now=now)


def _process_video_modality(
    case: CaseRecord,
    *,
    runtime: CaseRuntime,
    now: datetime,
) -> CaseRecord:
    from app.cases.pose_engine import PosturePoseEngine, resolve_video_analysis
    from app.cases.scene_engine import SceneDetectionEngine

    artifact = next((a for a in case.artifacts if a.modality == "video"), None)
    if artifact is None:
        return _replace_modality_status(case, "video", "failed", now=now)

    content = runtime.blob_store.get(artifact.bucket, artifact.object_key)
    if content is None:
        raise PermanentProcessingError(
            f"Artefato ausente: {artifact.bucket}/{artifact.object_key}"
        )

    kind = resolve_video_analysis(artifact.object_key)
    if kind == "pose":
        analysis = PosturePoseEngine().analyze_avi(content)
        frame_prefix = "pose"
        annotated = analysis.annotated_frames
    elif kind == "scene":
        analysis = SceneDetectionEngine().analyze_avi(content)
        frame_prefix = "scene"
        annotated = analysis.annotated_frames
    else:
        raise PermanentProcessingError(
            f"análise de vídeo não suportada: {kind}"
        )

    frame_artifacts: list[ArtifactRecord] = []
    for frame in annotated:
        frame_id = uuid.uuid4()
        object_key = (
            f"cases/{case.id}/video/frames/{frame_prefix}_{frame.index:03d}.png"
        )
        runtime.blob_store.put(
            bucket=artifact.bucket,
            object_key=object_key,
            content=frame.content,
            content_type=frame.content_type,
        )
        frame_artifacts.append(
            ArtifactRecord(
                id=frame_id,
                case_id=case.id,
                modality="video_frame",
                bucket=artifact.bucket,
                object_key=object_key,
                content_sha256=hashlib.sha256(frame.content).hexdigest(),
                content_type=frame.content_type,
                created_at=now,
            )
        )

    updated = _replace_modality_status(case, "video", "done", now=now)
    return _copy_case_meta(
        updated,
        now=now,
        artifacts=[*updated.artifacts, *frame_artifacts],
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
        audio_idempotency_key=case.audio_idempotency_key,
        audio_content_sha256=case.audio_content_sha256,
        prescriptions_idempotency_key=case.prescriptions_idempotency_key,
        prescriptions_content_sha256=case.prescriptions_content_sha256,
        justification=case.justification,
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
            return _process_audio_modality(current, runtime=ctx, now=now)
        if modality == "video":
            return _process_video_modality(current, runtime=ctx, now=now)
        if modality == "prescriptions":
            return _process_prescriptions_modality(current, runtime=ctx, now=now)
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
