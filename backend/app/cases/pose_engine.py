"""Análise Postural (Pose) — ADR 0007 / Épico 6 T6.3.

Interface alinhada a MediaPipe Pose; o backend padrão para fixtures/CI é
sintético (silhueta das AVIs versionadas). MediaPipe real pode ser ligado
depois via `LIMEN_POSE_BACKEND=mediapipe` quando a lib estiver disponível.
"""

from __future__ import annotations

import os
import struct
import zlib
from dataclasses import dataclass
from typing import Literal

from app.cases.video_avi import AviFrame, read_avi_bgr_frames
from app.cases.vitals_engine import ModalityRisk, VitalsAnomaly, risk_level_from_score

VideoAnalysisKind = Literal["pose", "scene"]


@dataclass(frozen=True)
class AnnotatedFrame:
    index: int
    content: bytes  # PNG
    content_type: str = "image/png"


@dataclass(frozen=True)
class PostureAnalysisResult:
    analysis: Literal["pose"]
    risk: ModalityRisk
    stability_score: float
    annotated_frames: tuple[AnnotatedFrame, ...]
    backend: str


def resolve_video_analysis(object_key: str) -> VideoAnalysisKind:
    key = object_key.lower()
    if "surgery" in key or "scene" in key:
        return "scene"
    return "pose"


def _png_rgb(width: int, height: int, rgb: bytes) -> bytes:
    """PNG RGB8 mínimo (stdlib) — sem Pillow."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"".join(
        b"\x00" + rgb[y * width * 3 : (y + 1) * width * 3] for y in range(height)
    )
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def _bgr_to_rgb(frame: AviFrame) -> bytes:
    out = bytearray(len(frame.bgr))
    for i in range(0, len(frame.bgr), 3):
        b, g, r = frame.bgr[i], frame.bgr[i + 1], frame.bgr[i + 2]
        out[i], out[i + 1], out[i + 2] = r, g, b
    return bytes(out)


def _silhouette_centroid(frame: AviFrame) -> tuple[float, float] | None:
    """Centroide dos pixels não-fundo (proxy de landmarks Pose)."""
    w, h = frame.width, frame.height
    sx = sy = n = 0
    for y in range(h):
        row = y * w * 3
        for x in range(w):
            i = row + x * 3
            b, g, r = frame.bgr[i], frame.bgr[i + 1], frame.bgr[i + 2]
            # Fundo fisio ≈ (90,70,40) BGR; figura é vermelha/azulada.
            if b < 80 and r > 120:
                sx += x
                sy += y
                n += 1
    if n == 0:
        return None
    return sx / n, sy / n


def _annotate_frame(frame: AviFrame, cx: float, cy: float) -> bytes:
    rgb = bytearray(_bgr_to_rgb(frame))
    w, h = frame.width, frame.height
    # Marca landmark (cruz amarela) no centroide — “anotação Pose”.
    ix, iy = int(cx), int(cy)
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            x, y = ix + dx, iy + dy
            if 0 <= x < w and 0 <= y < h:
                i = (y * w + x) * 3
                rgb[i : i + 3] = bytes((255, 220, 0))
    return _png_rgb(w, h, bytes(rgb))


class PosturePoseEngine:
    """Análise Postural no espírito MediaPipe Pose (ângulos/estabilidade)."""

    def analyze_avi(self, content: bytes) -> PostureAnalysisResult:
        backend = os.getenv("LIMEN_POSE_BACKEND", "synthetic").strip().lower()
        if backend == "mediapipe":
            # Pronto para o plug-in real; fixtures CI usam synthetic.
            raise RuntimeError(
                "LIMEN_POSE_BACKEND=mediapipe exige MediaPipe instalado "
                "(fora do escopo fechado T6.3 / fixtures sintéticas)"
            )

        frames = read_avi_bgr_frames(content)
        centroids: list[tuple[float, float]] = []
        annotated: list[AnnotatedFrame] = []
        for frame in frames:
            c = _silhouette_centroid(frame)
            if c is None:
                continue
            centroids.append(c)
            # Frames-chave: primeiro, meio e último com silhueta.
            if (
                len(annotated) == 0
                or frame.index == len(frames) // 2
                or frame.index == frames[-1].index
            ):
                annotated.append(
                    AnnotatedFrame(
                        index=frame.index,
                        content=_annotate_frame(frame, c[0], c[1]),
                    )
                )

        if not centroids:
            risk = ModalityRisk(
                score=0.55,
                level="MEDIO",
                anomalies=(
                    VitalsAnomaly(
                        metric="pose_visibility",
                        value=0.0,
                        detail="Silhueta postural não detectada",
                    ),
                ),
            )
            return PostureAnalysisResult(
                analysis="pose",
                risk=risk,
                stability_score=0.0,
                annotated_frames=(),
                backend="synthetic",
            )

        xs = [c[0] for c in centroids]
        ys = [c[1] for c in centroids]
        # Estabilidade: baixa dispersão vertical + movimento horizontal controlado.
        y_var = sum((y - sum(ys) / len(ys)) ** 2 for y in ys) / len(ys)
        x_span = max(xs) - min(xs)
        stability = max(0.0, min(1.0, 1.0 - (y_var / 40.0) - (abs(x_span - 20) / 40.0)))

        anomalies: list[VitalsAnomaly] = []
        if stability < 0.45:
            anomalies.append(
                VitalsAnomaly(
                    metric="postural_stability",
                    value=round(stability, 3),
                    detail="Instabilidade postural elevada",
                )
            )
        elif x_span > 18:
            anomalies.append(
                VitalsAnomaly(
                    metric="lateral_sway",
                    value=round(x_span, 2),
                    detail="Oscilação lateral do tronco",
                )
            )

        # Score de risco: estabilidade alta → risco baixo.
        score = max(0.05, min(0.95, 1.0 - stability * 0.85))
        if anomalies and score < 0.40:
            score = 0.42
        risk = ModalityRisk(
            score=score,
            level=risk_level_from_score(score),
            anomalies=tuple(anomalies),
        )
        # Garante evidência explícita de estabilidade quando não há anomalia.
        if not anomalies:
            anomalies_ok = (
                VitalsAnomaly(
                    metric="postural_stability",
                    value=round(stability, 3),
                    detail="Estabilidade postural dentro do esperado",
                ),
            )
            risk = ModalityRisk(
                score=risk.score,
                level=risk.level,
                anomalies=anomalies_ok,
            )

        # Dedup frames anotados por índice.
        uniq: dict[int, AnnotatedFrame] = {f.index: f for f in annotated}
        ordered = tuple(uniq[i] for i in sorted(uniq))

        return PostureAnalysisResult(
            analysis="pose",
            risk=risk,
            stability_score=stability,
            annotated_frames=ordered,
            backend="synthetic",
        )
