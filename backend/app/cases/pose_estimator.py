"""Estimador MediaPipe Pose injetável — Épico 11 / T11.2 / ADR 0030.

Opt-in via `LIMEN_POSE_BACKEND=mediapipe`. CI permanece em `synthetic`.
O SDK só entra no caminho real (lazy import); testes injetam `estimate`.
Retorno: centroide (x, y) em pixels do frame, ou None se sem pose visível.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.cases.video_avi import AviFrame

Centroid = tuple[float, float]
EstimateFn = Callable[["AviFrame"], Centroid | None]
PoseEstimator = Callable[["AviFrame"], Centroid | None]


def pose_backend_from_environment() -> str:
    return os.getenv("LIMEN_POSE_BACKEND", "synthetic").strip().lower() or "synthetic"


def estimate_centroid_with_mediapipe_sdk(frame: AviFrame) -> Centroid | None:
    """Chama MediaPipe Pose (lazy import — CI com synthetic não entra aqui)."""
    try:
        import mediapipe as mp
        import numpy as np
    except ImportError as exc:  # pragma: no cover - só com extra instalado
        raise RuntimeError(
            "LIMEN_POSE_BACKEND=mediapipe exige MediaPipe instalado "
            "(uv sync --extra mediapipe)"
        ) from exc

    rgb = np.frombuffer(frame.bgr, dtype=np.uint8).reshape(
        frame.height, frame.width, 3
    )[:, :, ::-1].copy()  # BGR → RGB

    with mp.solutions.pose.Pose(
        static_image_mode=True,
        model_complexity=0,
        enable_segmentation=False,
        min_detection_confidence=0.5,
    ) as pose:
        result = pose.process(rgb)

    if result.pose_landmarks is None:
        return None

    xs: list[float] = []
    ys: list[float] = []
    for lm in result.pose_landmarks.landmark:
        if lm.visibility is not None and lm.visibility < 0.5:
            continue
        xs.append(lm.x * frame.width)
        ys.append(lm.y * frame.height)
    if not xs:
        return None
    return sum(xs) / len(xs), sum(ys) / len(ys)


def create_mediapipe_pose_estimator(
    *,
    estimate: EstimateFn | None = None,
) -> PoseEstimator:
    """Factory injetável: testes passam `estimate`; produção usa o SDK."""
    estimate_fn = estimate or estimate_centroid_with_mediapipe_sdk

    def run(frame: AviFrame) -> Centroid | None:
        return estimate_fn(frame)

    return run
