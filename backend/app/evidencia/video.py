"""Geração de evidência commitável da modalidade vídeo (Épico 11 / ADR 0030)."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from app.cases.pose_engine import PosturePoseEngine
from app.cases.scene_engine import SceneDetectionEngine

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POSE_AVI = REPO_ROOT / "data" / "fixtures" / "video" / "video_physio.avi"
DEFAULT_SCENE_AVI = (
    REPO_ROOT / "data" / "fixtures" / "video" / "video_surgery_light.avi"
)
DEFAULT_OUT = REPO_ROOT / "data" / "evidencia" / "video"


@dataclass(frozen=True)
class EvidenciaVideoResult:
    output_dir: Path
    analysis_path: Path
    mode: str


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _rel(path: Path) -> str:
    if path.is_relative_to(REPO_ROOT):
        return str(path.relative_to(REPO_ROOT))
    return str(path)


@contextmanager
def _forced_backends(*, pose: str, yolo: str) -> Iterator[None]:
    prev_pose = os.environ.get("LIMEN_POSE_BACKEND")
    prev_yolo = os.environ.get("LIMEN_YOLO_BACKEND")
    os.environ["LIMEN_POSE_BACKEND"] = pose
    os.environ["LIMEN_YOLO_BACKEND"] = yolo
    try:
        yield
    finally:
        if prev_pose is None:
            os.environ.pop("LIMEN_POSE_BACKEND", None)
        else:
            os.environ["LIMEN_POSE_BACKEND"] = prev_pose
        if prev_yolo is None:
            os.environ.pop("LIMEN_YOLO_BACKEND", None)
        else:
            os.environ["LIMEN_YOLO_BACKEND"] = prev_yolo


def _pose_payload(avi: Path) -> dict[str, Any]:
    result = PosturePoseEngine().analyze_avi(avi.read_bytes())
    return {
        "source_avi": _rel(avi),
        "backend": result.backend,
        "analysis": result.analysis,
        "stability_score": result.stability_score,
        "modality_risk": {
            "score": result.risk.score,
            "level": result.risk.level,
            "anomalies": [asdict(a) for a in result.risk.anomalies],
        },
        "annotated_frame_count": len(result.annotated_frames),
        "annotated_frame_indexes": [f.index for f in result.annotated_frames],
    }


def _scene_payload(avi: Path) -> dict[str, Any]:
    result = SceneDetectionEngine().analyze_avi(avi.read_bytes())
    return {
        "source_avi": _rel(avi),
        "backend": result.backend,
        "analysis": result.analysis,
        "coco_classes": list(result.coco_classes),
        "heuristic_flags": dict(result.heuristic_flags),
        "modality_risk": {
            "score": result.risk.score,
            "level": result.risk.level,
            "anomalies": [asdict(a) for a in result.risk.anomalies],
        },
        "annotated_frame_count": len(result.annotated_frames),
        "annotated_frame_indexes": [f.index for f in result.annotated_frames],
    }


def run_evidencia_video(
    *,
    pose_avi: Path | None = None,
    scene_avi: Path | None = None,
    output_dir: Path | None = None,
    dry_run: bool = False,
) -> EvidenciaVideoResult:
    """Analisa fixtures de vídeo e grava JSON em `data/evidencia/video/`."""
    pose_path = pose_avi or DEFAULT_POSE_AVI
    scene_path = scene_avi or DEFAULT_SCENE_AVI
    out = output_dir or DEFAULT_OUT
    if not pose_path.is_file():
        raise FileNotFoundError(f"Fixture pose ausente: {pose_path}")
    if not scene_path.is_file():
        raise FileNotFoundError(f"Fixture scene ausente: {scene_path}")

    mode = "dry-run" if dry_run else "video-live"
    if dry_run:
        with _forced_backends(pose="synthetic", yolo="synthetic"):
            pose = _pose_payload(pose_path)
            scene = _scene_payload(scene_path)
    else:
        # Live: usa LIMEN_* do ambiente (ultralytics / mediapipe).
        pose = _pose_payload(pose_path)
        scene = _scene_payload(scene_path)

    payload = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "mode": mode,
        "disclaimer": (
            "Protótipo acadêmico Limen — demonstração de visão computacional, "
            "sem diagnóstico clínico."
        ),
        "pose": pose,
        "scene": scene,
    }

    analysis_path = out / "analysis.json"
    _write_json(analysis_path, payload)
    _write_json(out / "pose.json", {**pose, "mode": mode})
    _write_json(out / "scene.json", {**scene, "mode": mode})
    return EvidenciaVideoResult(
        output_dir=out, analysis_path=analysis_path, mode=mode
    )
