"""TDD T11.2 — MediaPipe Pose injetável para Análise Postural (sem SDK no CI)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.cases.pose_engine import PosturePoseEngine
from app.cases.pose_estimator import (
    create_mediapipe_pose_estimator,
    pose_backend_from_environment,
)
from app.cases.video_avi import AviFrame, read_avi_bgr_frames

REPO_ROOT = Path(__file__).resolve().parents[2]
VIDEO_PHYSIO = (
    REPO_ROOT / "data" / "fixtures" / "video" / "video_physio.avi"
).read_bytes()


@pytest.fixture(autouse=True)
def reset_pose_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIMEN_POSE_BACKEND", "synthetic")
    yield


def test_pose_backend_defaults_to_synthetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LIMEN_POSE_BACKEND", raising=False)
    assert pose_backend_from_environment() == "synthetic"


def test_pose_backend_reads_mediapipe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_POSE_BACKEND", "mediapipe")
    assert pose_backend_from_environment() == "mediapipe"


def test_mediapipe_without_inject_and_without_sdk_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_POSE_BACKEND", "mediapipe")
    engine = PosturePoseEngine()
    with pytest.raises(RuntimeError, match="[Mm]edia[Pp]ipe"):
        engine.analyze_avi(VIDEO_PHYSIO)


def test_mediapipe_uses_injected_estimator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_POSE_BACKEND", "mediapipe")
    frames = read_avi_bgr_frames(VIDEO_PHYSIO)
    calls: list[int] = []

    def fake_estimate(frame: AviFrame) -> tuple[float, float] | None:
        calls.append(frame.index)
        # Centroide estável → estabilidade alta / risco baixo (heurística E6.1).
        return (20.0 + frame.index * 0.1, 24.0)

    engine = PosturePoseEngine(estimator=fake_estimate)
    result = engine.analyze_avi(VIDEO_PHYSIO)

    assert result.backend == "mediapipe"
    assert result.analysis == "pose"
    assert result.stability_score > 0.0
    assert result.annotated_frames
    assert all(f.content.startswith(b"\x89PNG") for f in result.annotated_frames)
    assert calls == [f.index for f in frames]


def test_create_mediapipe_estimator_uses_injected_estimate() -> None:
    seen: list[tuple[int, int]] = []

    def fake_estimate(frame: AviFrame) -> tuple[float, float] | None:
        seen.append((frame.width, frame.height))
        return (1.0, 2.0)

    estimate = create_mediapipe_pose_estimator(estimate=fake_estimate)
    frame = AviFrame(index=0, width=8, height=6, bgr=b"\x00" * (8 * 6 * 3))
    assert estimate(frame) == (1.0, 2.0)
    assert seen == [(8, 6)]


def test_synthetic_backend_ignores_injected_estimator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_POSE_BACKEND", "synthetic")

    def boom(_frame: AviFrame) -> tuple[float, float] | None:
        raise AssertionError("estimator não deve ser chamado no synthetic")

    engine = PosturePoseEngine(estimator=boom)
    result = engine.analyze_avi(VIDEO_PHYSIO)
    assert result.backend == "synthetic"
    assert result.annotated_frames
