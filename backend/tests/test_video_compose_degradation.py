"""TDD T11.3 — wiring worker-video/Compose + degradação independente Pose↔Scene."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.cases import runtime as runtime_mod
from app.cases.pose_engine import PosturePoseEngine
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
VIDEO_PHYSIO = (
    REPO_ROOT / "data" / "fixtures" / "video" / "video_physio.avi"
).read_bytes()
VIDEO_SURGERY = (
    REPO_ROOT / "data" / "fixtures" / "video" / "video_surgery_light.avi"
).read_bytes()
VITALS_CSV = (
    REPO_ROOT / "data" / "fixtures" / "vitals" / "vitals_normal.csv"
).read_bytes()


@pytest.fixture(autouse=True)
def reset_runtime_and_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    monkeypatch.setenv("LIMEN_YOLO_BACKEND", "synthetic")
    monkeypatch.setenv("LIMEN_POSE_BACKEND", "synthetic")
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def test_dockerfile_supports_optional_video_extras_arg() -> None:
    text = (REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "LIMEN_UV_EXTRAS" in text
    assert "uv sync --frozen --no-dev" in text
    # Default sem extras (API/worker leves); extras só quando ARG preenchido.
    assert 'LIMEN_UV_EXTRAS=""' in text or "LIMEN_UV_EXTRAS=''" in text


def test_compose_worker_video_exports_pose_and_yolo_backends() -> None:
    text = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    video_block = text.split("\n  worker-video:")[1].split("\n  outbox-reconciler:")[0]
    assert "LIMEN_YOLO_BACKEND" in video_block
    assert "LIMEN_POSE_BACKEND" in video_block
    assert "synthetic" in video_block
    # Build padrão do worker-video não passa ARG de extras (só o override).
    assert "args:" not in video_block


def test_compose_backend_does_not_install_video_extras_by_default() -> None:
    dockerfile = (REPO_ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    backend_block = compose.split("\n  backend:")[1].split("\n  worker:")[0]
    assert "ultralytics" not in backend_block.lower()
    assert "mediapipe" not in backend_block.lower()
    assert 'ARG LIMEN_UV_EXTRAS=""' in dockerfile or "ARG LIMEN_UV_EXTRAS=''" in dockerfile


def test_video_real_compose_override_exists() -> None:
    path = REPO_ROOT / "docker-compose.video-real.yml"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "worker-video" in text
    assert "LIMEN_UV_EXTRAS" in text
    assert "ultralytics" in text
    assert "mediapipe" in text
    assert "LIMEN_YOLO_BACKEND" in text
    assert "LIMEN_POSE_BACKEND" in text


def test_yolo_ultralytics_failure_does_not_break_pose_synthetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_YOLO_BACKEND", "ultralytics")
    monkeypatch.setenv("LIMEN_POSE_BACKEND", "synthetic")

    with pytest.raises(RuntimeError, match="ultralytics"):
        SceneDetectionEngine().analyze_avi(VIDEO_SURGERY)

    pose = PosturePoseEngine().analyze_avi(VIDEO_PHYSIO)
    assert pose.backend == "synthetic"
    assert pose.annotated_frames


def test_mediapipe_failure_does_not_break_scene_synthetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_POSE_BACKEND", "mediapipe")
    monkeypatch.setenv("LIMEN_YOLO_BACKEND", "synthetic")

    with pytest.raises(RuntimeError, match="[Mm]edia[Pp]ipe"):
        PosturePoseEngine().analyze_avi(VIDEO_PHYSIO)

    scene = SceneDetectionEngine().analyze_avi(VIDEO_SURGERY)
    assert scene.backend == "synthetic"
    assert scene.heuristic_flags["person_present"] is True


def test_process_video_marks_failed_when_ultralytics_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_YOLO_BACKEND", "ultralytics")
    monkeypatch.setenv("LIMEN_POSE_BACKEND", "synthetic")

    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    vitals_id = uuid.uuid4()
    video_id = uuid.uuid4()
    object_key = f"cases/{case_id}/video/video_surgery_light.avi"
    vitals_key = f"cases/{case_id}/vitals.csv"
    blob_store.put(
        bucket="limen",
        object_key=object_key,
        content=VIDEO_SURGERY,
        content_type="video/x-msvideo",
    )
    blob_store.put(
        bucket="limen",
        object_key=vitals_key,
        content=VITALS_CSV,
        content_type="text/csv",
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
                    modality="vitals",
                    status="done",
                    artifact_id=vitals_id,
                    created_at=now,
                    updated_at=now,
                ),
                ModalityRecord(
                    id=uuid.uuid4(),
                    case_id=case_id,
                    modality="video",
                    status="pending",
                    artifact_id=video_id,
                    created_at=now,
                    updated_at=now,
                ),
            ],
            artifacts=[
                ArtifactRecord(
                    id=vitals_id,
                    case_id=case_id,
                    modality="vitals",
                    bucket="limen",
                    object_key=vitals_key,
                    content_sha256="v",
                    content_type="text/csv",
                    created_at=now,
                ),
                ArtifactRecord(
                    id=video_id,
                    case_id=case_id,
                    modality="video",
                    bucket="limen",
                    object_key=object_key,
                    content_sha256="y",
                    content_type="video/x-msvideo",
                    created_at=now,
                ),
            ],
            alerts=(),
        )
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)

    updated = process_modality_for_case(case_id, "video")
    assert updated is not None
    video = next(m for m in updated.modalities if m.modality == "video")
    assert video.status == "failed"
    # Vitais intactos → Caso pode fechar com falha parcial.
    assert updated.status == "done"
    vitals = next(m for m in updated.modalities if m.modality == "vitals")
    assert vitals.status == "done"
