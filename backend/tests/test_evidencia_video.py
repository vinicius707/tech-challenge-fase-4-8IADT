"""TDD T11.4 — evidência de vídeo + orquestrador real (dry-run sem YOLO/MediaPipe)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.evidencia.video import run_evidencia_video

REPO_ROOT = Path(__file__).resolve().parents[2]
VIDEO_DIR = REPO_ROOT / "data" / "fixtures" / "video"
EVIDENCIA_DIR = REPO_ROOT / "data" / "evidencia" / "video"
SCRIPT_VIDEO_SH = REPO_ROOT / "scripts" / "gerar-evidencia-video.sh"
SCRIPT_REAL_SH = REPO_ROOT / "scripts" / "gerar-evidencia-real.sh"
SCRIPT_VIDEO_PY = REPO_ROOT / "scripts" / "gerar_evidencia_video.py"


def test_evidencia_video_scripts_exist_and_orchestrator_delegates() -> None:
    assert SCRIPT_VIDEO_SH.is_file()
    assert SCRIPT_REAL_SH.is_file()
    assert SCRIPT_VIDEO_PY.is_file()
    real = SCRIPT_REAL_SH.read_text(encoding="utf-8")
    assert "gerar-evidencia-audio.sh" in real
    assert "gerar-evidencia-video.sh" in real
    video = SCRIPT_VIDEO_SH.read_text(encoding="utf-8")
    assert "gerar_evidencia_video.py" in video
    assert "data/evidencia/video" in video or "evidencia" in video


def test_run_evidencia_video_dry_run_writes_json(tmp_path: Path) -> None:
    out = tmp_path / "evidencia"
    result = run_evidencia_video(output_dir=out, dry_run=True)
    assert result.mode == "dry-run"
    assert result.analysis_path.is_file()

    analysis = json.loads(result.analysis_path.read_text(encoding="utf-8"))
    assert analysis["mode"] == "dry-run"
    assert analysis["pose"]["backend"] == "synthetic"
    assert analysis["scene"]["backend"] == "synthetic"
    assert analysis["pose"]["stability_score"] >= 0.0
    assert analysis["scene"]["heuristic_flags"]["person_present"] is True
    assert analysis["pose"]["annotated_frame_count"] >= 1
    assert analysis["scene"]["annotated_frame_count"] >= 1
    assert (out / "pose.json").is_file()
    assert (out / "scene.json").is_file()


def test_cli_dry_run_writes_under_tmp(tmp_path: Path) -> None:
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_VIDEO_PY),
            "--dry-run",
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={
            **dict(os.environ),
            "PYTHONPATH": str(REPO_ROOT / "backend"),
        },
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert (out / "analysis.json").is_file()


def test_evidencia_video_readme_documents_scripts() -> None:
    readme = (EVIDENCIA_DIR / "README.md").read_text(encoding="utf-8")
    assert "gerar-evidencia-video" in readme
    assert "dry-run" in readme.lower() or "--dry-run" in readme
    assert "physio" in readme.lower() or "surgery" in readme.lower()


def test_fixtures_video_exist_for_evidencia() -> None:
    assert (VIDEO_DIR / "video_physio.avi").is_file()
    assert (VIDEO_DIR / "video_surgery_light.avi").is_file()
