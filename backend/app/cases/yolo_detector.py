"""Detector YOLOv8 (Ultralytics) injetável — Épico 11 / T11.1 / ADR 0030.

Opt-in via `LIMEN_YOLO_BACKEND=ultralytics`. CI permanece em `synthetic`.
O SDK/pesos só entram no caminho real (lazy import); testes injetam `predict`.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.cases.scene_engine import CocoDetection
    from app.cases.video_avi import AviFrame

PredictFn = Callable[..., list["CocoDetection"]]
FrameDetector = Callable[["AviFrame"], list["CocoDetection"]]

DEFAULT_YOLO_MODEL = "yolov8n.pt"


def yolo_backend_from_environment() -> str:
    return os.getenv("LIMEN_YOLO_BACKEND", "synthetic").strip().lower() or "synthetic"


def predict_with_ultralytics_sdk(
    frame: AviFrame,
    *,
    model_name: str = DEFAULT_YOLO_MODEL,
) -> list[CocoDetection]:
    """Chama Ultralytics YOLO (pode baixar pesos). Lazy import — CI não entra aqui."""
    from app.cases.scene_engine import CocoDetection

    try:
        import numpy as np
        from ultralytics import YOLO
    except ImportError as exc:  # pragma: no cover - só com extra instalado
        raise RuntimeError(
            "LIMEN_YOLO_BACKEND=ultralytics exige ultralytics instalado "
            "(uv sync --extra ultralytics)"
        ) from exc

    # BGR bytes → HxWx3 uint8 (contrato Ultralytics / OpenCV).
    arr = np.frombuffer(frame.bgr, dtype=np.uint8).reshape(
        frame.height, frame.width, 3
    )
    model = YOLO(model_name)
    results = model.predict(source=arr, verbose=False)
    out: list[CocoDetection] = []
    for result in results:
        names = result.names or {}
        boxes = result.boxes
        if boxes is None:
            continue
        for box in boxes:
            cls_id = int(box.cls[0].item())
            label = str(names.get(cls_id, cls_id))
            xyxy = box.xyxy[0].tolist()
            x0, y0, x1, y1 = (int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3]))
            conf = float(box.conf[0].item()) if box.conf is not None else 1.0
            out.append(
                CocoDetection(label=label, box=(x0, y0, x1, y1), confidence=conf)
            )
    return out


def create_ultralytics_frame_detector(
    *,
    model_name: str = DEFAULT_YOLO_MODEL,
    predict: PredictFn | None = None,
) -> FrameDetector:
    """Factory injetável: testes passam `predict`; produção usa o SDK."""
    predict_fn = predict or predict_with_ultralytics_sdk

    def detect(frame: AviFrame) -> list[CocoDetection]:
        return predict_fn(frame, model_name=model_name)

    return detect
