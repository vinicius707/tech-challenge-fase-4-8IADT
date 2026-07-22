"""TDD T6.4 — Detecção em Cena (YOLO COCO + heurísticas) em fixture cirurgia leve."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.cases import runtime as runtime_mod
from app.cases.pose_engine import resolve_video_analysis
from app.cases.processing import process_modality_for_case
from app.cases.scene_engine import SceneDetectionEngine
from app.cases.service import (
    ArtifactRecord,
    CaseRecord,
    InMemoryCaseStore,
    ModalityRecord,
)
from app.cases.storage import InMemoryArtifactBlobStore
from app.outbox import completion as completion_mod

REPO_ROOT = Path(__file__).resolve().parents[2]
VIDEO_SURGERY = (
    REPO_ROOT / "data" / "fixtures" / "video" / "video_surgery_light.avi"
).read_bytes()

# Claims clínicos proibidos (ADR 0007 / CONTEXT.md).
FORBIDDEN_CLAIM_TOKENS = (
    "sangramento",
    "bleeding",
    "hemorragia",
    "diagnóstico",
    "diagnosis",
)


@pytest.fixture(autouse=True)
def reset_runtime() -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def test_resolve_video_analysis_routes_surgery_to_scene() -> None:
    assert resolve_video_analysis("cases/x/video/video_surgery_light.avi") == "scene"


def test_scene_engine_analyzes_surgery_fixture() -> None:
    engine = SceneDetectionEngine()
    result = engine.analyze_avi(VIDEO_SURGERY)

    assert result.analysis == "scene"
    assert result.risk.score >= 0.0
    assert result.risk.level in {"BAIXO", "MEDIO", "ALTO"}
    assert result.coco_classes, "espera classes COCO detectadas"
    assert "person" in result.coco_classes
    assert result.heuristic_flags, "espera flags heurísticas documentadas"
    assert result.heuristic_flags.get("person_present") is True
    assert result.annotated_frames, "espera frames-chave anotados"
    assert all(frame.content.startswith(b"\x89PNG") for frame in result.annotated_frames)

    blob = " ".join(
        [
            " ".join(result.coco_classes),
            " ".join(f"{k}={v}" for k, v in result.heuristic_flags.items()),
            " ".join(a.detail for a in result.risk.anomalies),
            " ".join(a.metric for a in result.risk.anomalies),
        ]
    ).lower()
    for token in FORBIDDEN_CLAIM_TOKENS:
        assert token not in blob, f"claim clínico proibido: {token}"


def test_process_surgery_video_marks_done_and_stores_frame_artifacts() -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    object_key = f"cases/{case_id}/video/video_surgery_light.avi"
    blob_store.put(
        bucket="limen",
        object_key=object_key,
        content=VIDEO_SURGERY,
        content_type="video/x-msvideo",
    )
    case_store.save(
        CaseRecord(
            id=case_id,
            patient_id=uuid.uuid4(),
            status="pending",
            risk_score=None,
            risk_level=None,
            idempotency_key=str(uuid.uuid4()),
            content_sha256="x",
            created_at=now,
            updated_at=now,
            modalities=[
                ModalityRecord(
                    id=uuid.uuid4(),
                    case_id=case_id,
                    modality="video",
                    status="pending",
                    artifact_id=artifact_id,
                    created_at=now,
                    updated_at=now,
                )
            ],
            artifacts=[
                ArtifactRecord(
                    id=artifact_id,
                    case_id=case_id,
                    modality="video",
                    bucket="limen",
                    object_key=object_key,
                    content_sha256="x",
                    content_type="video/x-msvideo",
                    created_at=now,
                )
            ],
        )
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)

    result = process_modality_for_case(case_id, "video")
    assert result is not None
    video_mod = next(m for m in result.modalities if m.modality == "video")
    assert video_mod.status == "done"

    frame_arts = [a for a in result.artifacts if a.modality == "video_frame"]
    assert frame_arts, "frames anotados devem virar Artefatos"
    assert any("scene_" in a.object_key for a in frame_arts)
    for art in frame_arts:
        content = blob_store.get(art.bucket, art.object_key)
        assert content is not None
        assert content.startswith(b"\x89PNG")

    assert result.status == "done"
    assert result.risk_level is not None
