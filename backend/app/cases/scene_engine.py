"""Detecção em Cena (YOLOv8 COCO + heurísticas) — ADR 0007 / Épico 6 T6.4.

Interface alinhada a YOLOv8 pré-treinado COCO; o backend padrão para
fixtures/CI é sintético (cores/geometria das AVIs versionadas). Ultralytics
real pode ser ligado depois via `LIMEN_YOLO_BACKEND=ultralytics` quando a
lib estiver disponível.

Heurísticas documentadas (demo de visão computacional — sem claim clínico):

- `person_present`: classe COCO `person` em fração relevante dos frames
- `generic_object_present`: objeto genérico (proxy COCO `bottle`) co-ocorrendo
- `scene_occupied`: pessoa + objeto genérico na mesma cena

Proibido: sangramento, diagnóstico cirúrgico, fine-tune clínico.
"""

from __future__ import annotations

import os
import struct
import zlib
from dataclasses import dataclass
from typing import Literal

from app.cases.pose_engine import AnnotatedFrame
from app.cases.video_avi import AviFrame, read_avi_bgr_frames
from app.cases.vitals_engine import ModalityRisk, VitalsAnomaly, risk_level_from_score

# Classes COCO usadas nesta demo (subconjunto genérico — sem rótulo clínico).
COCO_PERSON = "person"
COCO_GENERIC_OBJECT = "bottle"  # proxy de objeto genérico na fixture


@dataclass(frozen=True)
class SceneDetectionResult:
    analysis: Literal["scene"]
    risk: ModalityRisk
    coco_classes: tuple[str, ...]
    heuristic_flags: dict[str, bool]
    annotated_frames: tuple[AnnotatedFrame, ...]
    backend: str


def _png_rgb(width: int, height: int, rgb: bytes) -> bytes:
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


def _bbox_from_mask(
    frame: AviFrame,
    *,
    match,
) -> tuple[int, int, int, int] | None:
    """Bounding box axis-aligned dos pixels que passam no predicado BGR."""
    w, h = frame.width, frame.height
    min_x, min_y = w, h
    max_x, max_y = -1, -1
    for y in range(h):
        row = y * w * 3
        for x in range(w):
            i = row + x * 3
            b, g, r = frame.bgr[i], frame.bgr[i + 1], frame.bgr[i + 2]
            if match(b, g, r):
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y
    if max_x < 0:
        return None
    return min_x, min_y, max_x, max_y


def _is_person_pixel(b: int, g: int, r: int) -> bool:
    # Figura escura da fixture surgery (≈ 50,50,50 BGR).
    return b < 70 and g < 70 and r < 70 and (b + g + r) < 180


def _is_object_pixel(b: int, g: int, r: int) -> bool:
    # Objeto genérico azulado/marrom (≈ 180,120,60 BGR).
    return b > 140 and 90 < g < 150 and r < 90


def _draw_box(
    rgb: bytearray,
    width: int,
    height: int,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = box
    for x in range(x0, x1 + 1):
        for y in (y0, y1):
            if 0 <= x < width and 0 <= y < height:
                i = (y * width + x) * 3
                rgb[i : i + 3] = bytes(color)
    for y in range(y0, y1 + 1):
        for x in (x0, x1):
            if 0 <= x < width and 0 <= y < height:
                i = (y * width + x) * 3
                rgb[i : i + 3] = bytes(color)


def _annotate_detections(
    frame: AviFrame,
    person_box: tuple[int, int, int, int] | None,
    object_box: tuple[int, int, int, int] | None,
) -> bytes:
    rgb = bytearray(_bgr_to_rgb(frame))
    w, h = frame.width, frame.height
    if person_box is not None:
        _draw_box(rgb, w, h, person_box, (0, 220, 80))  # verde = person
    if object_box is not None:
        _draw_box(rgb, w, h, object_box, (255, 160, 0))  # laranja = objeto
    return _png_rgb(w, h, bytes(rgb))


class SceneDetectionEngine:
    """Detecção em Cena no espírito YOLOv8 COCO + regras heurísticas."""

    def analyze_avi(self, content: bytes) -> SceneDetectionResult:
        backend = os.getenv("LIMEN_YOLO_BACKEND", "synthetic").strip().lower()
        if backend == "ultralytics":
            raise RuntimeError(
                "LIMEN_YOLO_BACKEND=ultralytics exige ultralytics instalado "
                "(fora do escopo fechado T6.4 / fixtures sintéticas)"
            )

        frames = read_avi_bgr_frames(content)
        person_hits = 0
        object_hits = 0
        annotated: list[AnnotatedFrame] = []
        classes_seen: set[str] = set()

        for frame in frames:
            person_box = _bbox_from_mask(frame, match=_is_person_pixel)
            object_box = _bbox_from_mask(frame, match=_is_object_pixel)
            if person_box is not None:
                person_hits += 1
                classes_seen.add(COCO_PERSON)
            if object_box is not None:
                object_hits += 1
                classes_seen.add(COCO_GENERIC_OBJECT)

            if person_box is not None or object_box is not None:
                if (
                    len(annotated) == 0
                    or frame.index == len(frames) // 2
                    or frame.index == frames[-1].index
                ):
                    annotated.append(
                        AnnotatedFrame(
                            index=frame.index,
                            content=_annotate_detections(
                                frame, person_box, object_box
                            ),
                        )
                    )

        n = max(len(frames), 1)
        person_present = (person_hits / n) >= 0.5
        generic_object_present = (object_hits / n) >= 0.5
        scene_occupied = person_present and generic_object_present

        flags = {
            "person_present": person_present,
            "generic_object_present": generic_object_present,
            "scene_occupied": scene_occupied,
        }

        anomalies: list[VitalsAnomaly] = []
        if not person_present:
            anomalies.append(
                VitalsAnomaly(
                    metric="scene_person",
                    value=round(person_hits / n, 3),
                    detail="Presença de pessoa (COCO person) abaixo do limiar",
                )
            )
        if not generic_object_present:
            anomalies.append(
                VitalsAnomaly(
                    metric="scene_object",
                    value=round(object_hits / n, 3),
                    detail="Objeto genérico (COCO bottle proxy) abaixo do limiar",
                )
            )
        if scene_occupied and not anomalies:
            anomalies.append(
                VitalsAnomaly(
                    metric="scene_occupancy",
                    value=1.0,
                    detail="Cena ocupada: pessoa e objeto genérico co-ocorrem",
                )
            )

        # Risco demo: cena estável (ocupada) → BAIXO; ausência de pessoa eleva.
        if not person_present:
            score = 0.55
        elif not generic_object_present:
            score = 0.42
        else:
            score = 0.18
        risk = ModalityRisk(
            score=score,
            level=risk_level_from_score(score),
            anomalies=tuple(anomalies),
        )

        uniq: dict[int, AnnotatedFrame] = {f.index: f for f in annotated}
        ordered = tuple(uniq[i] for i in sorted(uniq))

        return SceneDetectionResult(
            analysis="scene",
            risk=risk,
            coco_classes=tuple(sorted(classes_seen)),
            heuristic_flags=flags,
            annotated_frames=ordered,
            backend="synthetic",
        )
