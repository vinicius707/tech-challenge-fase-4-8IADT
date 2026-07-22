"""TDD T6.3 — Análise Postural (Pose) em fixture fisio + frames no MinIO."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.cases import runtime as runtime_mod
from app.cases.pose_engine import PosturePoseEngine, resolve_video_analysis
from app.cases.processing import process_modality_for_case
from app.cases.service import (
    ArtifactRecord,
    CaseRecord,
    InMemoryCaseStore,
    ModalityRecord,
)
from app.cases.storage import InMemoryArtifactBlobStore
from app.outbox import completion as completion_mod

REPO_ROOT = Path(__file__).resolve().parents[2]
VIDEO_PHYSIO = (
    REPO_ROOT / "data" / "fixtures" / "video" / "video_physio.avi"
).read_bytes()


@pytest.fixture(autouse=True)
def reset_runtime() -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def test_resolve_video_analysis_routes_physio_to_pose() -> None:
    assert resolve_video_analysis("cases/x/video/video_physio.avi") == "pose"
    assert resolve_video_analysis("cases/x/video/clip.avi") == "pose"
    assert resolve_video_analysis("cases/x/video/video_surgery_light.avi") == "scene"


def test_posture_engine_analyzes_physio_fixture() -> None:
    engine = PosturePoseEngine()
    result = engine.analyze_avi(VIDEO_PHYSIO)

    assert result.analysis == "pose"
    assert result.risk.score >= 0.0
    assert result.risk.level in {"BAIXO", "MEDIO", "ALTO"}
    # Evidência de estabilidade ou anomalia postural explícita.
    assert result.stability_score is not None
    assert result.stability_score >= 0.0
    assert result.annotated_frames, "espera frames-chave anotados"
    assert all(frame.content.startswith(b"\x89PNG") for frame in result.annotated_frames)
    assert result.risk.anomalies or result.stability_score > 0.0


def test_process_physio_video_marks_done_and_stores_frame_artifacts() -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    object_key = f"cases/{case_id}/video/video_physio.avi"
    blob_store.put(
        bucket="limen",
        object_key=object_key,
        content=VIDEO_PHYSIO,
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
    for art in frame_arts:
        content = blob_store.get(art.bucket, art.object_key)
        assert content is not None
        assert content.startswith(b"\x89PNG")

    assert result.status == "done"
    assert result.risk_level is not None
