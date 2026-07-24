#!/usr/bin/env python3
"""CLI — evidência de vídeo Pose + Scene (Épico 11 / T11.4).

Uso:
  cd backend && uv run python ../scripts/gerar_evidencia_video.py --dry-run
  LIMEN_POSE_BACKEND=mediapipe LIMEN_YOLO_BACKEND=ultralytics \\
    cd backend && uv run python ../scripts/gerar_evidencia_video.py

Prefira: ./scripts/gerar-evidencia-video.sh [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.evidencia.video import run_evidencia_video  # noqa: E402


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera evidência de vídeo (JSON).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Sem Ultralytics/MediaPipe: engines synthetic nas fixtures AVI",
    )
    parser.add_argument("--pose-avi", type=Path, default=None)
    parser.add_argument("--scene-avi", type=Path, default=None)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Diretório de saída (default: data/evidencia/video)",
    )
    args = parser.parse_args(argv)

    _load_dotenv(REPO_ROOT / ".env")
    dry_run = args.dry_run or os.getenv("LIMEN_EVIDENCIA_DRY_RUN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not dry_run:
        os.environ.setdefault("LIMEN_POSE_BACKEND", "mediapipe")
        os.environ.setdefault("LIMEN_YOLO_BACKEND", "ultralytics")

    result = run_evidencia_video(
        pose_avi=args.pose_avi,
        scene_avi=args.scene_avi,
        output_dir=args.out,
        dry_run=dry_run,
    )
    print(f"Evidência ({result.mode}) em {result.output_dir}")
    print(f"  - {result.analysis_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
