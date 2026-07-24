"""TDD T11.1 — YOLOv8 Ultralytics injetável para Detecção em Cena (sem pesos no CI)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.cases.scene_engine import (
    COCO_GENERIC_OBJECT,
    COCO_PERSON,
    CocoDetection,
    SceneDetectionEngine,
)
from app.cases.video_avi import AviFrame, read_avi_bgr_frames
from app.cases.yolo_detector import (
    create_ultralytics_frame_detector,
    yolo_backend_from_environment,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
VIDEO_SURGERY = (
    REPO_ROOT / "data" / "fixtures" / "video" / "video_surgery_light.avi"
).read_bytes()


@pytest.fixture(autouse=True)
def reset_yolo_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIMEN_YOLO_BACKEND", "synthetic")
    yield


def test_yolo_backend_defaults_to_synthetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LIMEN_YOLO_BACKEND", raising=False)
    assert yolo_backend_from_environment() == "synthetic"


def test_yolo_backend_reads_ultralytics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_YOLO_BACKEND", "ultralytics")
    assert yolo_backend_from_environment() == "ultralytics"


def test_ultralytics_without_inject_and_without_sdk_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_YOLO_BACKEND", "ultralytics")
    engine = SceneDetectionEngine()
    with pytest.raises(RuntimeError, match="ultralytics"):
        engine.analyze_avi(VIDEO_SURGERY)


def test_ultralytics_uses_injected_detector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_YOLO_BACKEND", "ultralytics")
    frames = read_avi_bgr_frames(VIDEO_SURGERY)
    calls: list[int] = []

    def fake_detect(frame: AviFrame) -> list[CocoDetection]:
        calls.append(frame.index)
        # Pessoa + bottle em todos os frames → cena ocupada (heurística E6.1).
        w, h = frame.width, frame.height
        return [
            CocoDetection(
                label=COCO_PERSON,
                box=(2, 2, max(3, w // 3), max(3, h // 2)),
                confidence=0.9,
            ),
            CocoDetection(
                label=COCO_GENERIC_OBJECT,
                box=(w // 2, h // 2, w - 2, h - 2),
                confidence=0.8,
            ),
        ]

    engine = SceneDetectionEngine(detector=fake_detect)
    result = engine.analyze_avi(VIDEO_SURGERY)

    assert result.backend == "ultralytics"
    assert result.analysis == "scene"
    assert COCO_PERSON in result.coco_classes
    assert COCO_GENERIC_OBJECT in result.coco_classes
    assert result.heuristic_flags["person_present"] is True
    assert result.heuristic_flags["generic_object_present"] is True
    assert result.heuristic_flags["scene_occupied"] is True
    assert result.annotated_frames
    assert all(f.content.startswith(b"\x89PNG") for f in result.annotated_frames)
    assert calls == [f.index for f in frames]


def test_create_ultralytics_detector_uses_injected_predict() -> None:
    seen: list[tuple[int, int]] = []

    def fake_predict(
        frame: AviFrame, *, model_name: str
    ) -> list[CocoDetection]:
        assert model_name == "yolov8n.pt"
        seen.append((frame.width, frame.height))
        return [
            CocoDetection(label=COCO_PERSON, box=(0, 0, 4, 4), confidence=0.99),
        ]

    detect = create_ultralytics_frame_detector(predict=fake_predict)
    frame = AviFrame(index=0, width=8, height=6, bgr=b"\x00" * (8 * 6 * 3))
    out = detect(frame)
    assert out[0].label == COCO_PERSON
    assert seen == [(8, 6)]


def test_synthetic_backend_ignores_injected_detector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CI permanece no caminho sintético mesmo se um detector for passado."""
    monkeypatch.setenv("LIMEN_YOLO_BACKEND", "synthetic")

    def boom(_frame: AviFrame) -> list[CocoDetection]:
        raise AssertionError("detector não deve ser chamado no synthetic")

    engine = SceneDetectionEngine(detector=boom)
    result = engine.analyze_avi(VIDEO_SURGERY)
    assert result.backend == "synthetic"
    assert result.heuristic_flags["person_present"] is True
