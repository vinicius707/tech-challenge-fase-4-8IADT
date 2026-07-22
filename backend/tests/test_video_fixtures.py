"""TDD T6.1 — contrato das fixtures de vídeo (spec epic-06 E6.1)."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VIDEO_DIR = REPO_ROOT / "data" / "fixtures" / "video"
PREPARE_SCRIPT = REPO_ROOT / "scripts" / "prepare_video_fixtures.py"

REQUIRED_FILES = (
    "video_physio.avi",
    "video_surgery_light.avi",
    "manifest.json",
    "README.md",
)

MANIFEST_REQUIRED_KEYS = ("version", "seed", "fixtures")
FIXTURE_REQUIRED_KEYS = ("file", "scenario", "analysis", "width", "height", "frames")

FORBIDDEN_NAME_PATTERNS = re.compile(
    r"(cpf|prontuario|patient_id|ssn|sangramento|bleed)",
    re.IGNORECASE,
)

# Limite frouxo para caber no Git sem brutos grandes.
MAX_BYTES_PER_CLIP = 250_000


@pytest.mark.parametrize("filename", REQUIRED_FILES)
def test_video_fixture_file_exists(filename: str) -> None:
    path = VIDEO_DIR / filename
    assert path.is_file(), f"Fixture ausente: {path}"


def test_video_clips_are_riff_avi_and_small() -> None:
    for name in ("video_physio.avi", "video_surgery_light.avi"):
        path = VIDEO_DIR / name
        data = path.read_bytes()
        assert len(data) > 64, f"Clip vazio demais: {name}"
        assert len(data) <= MAX_BYTES_PER_CLIP, f"Clip grande demais para Git: {name}"
        assert data[:4] == b"RIFF", f"Não é RIFF: {name}"
        assert data[8:12] == b"AVI ", f"Não é AVI: {name}"
        assert FORBIDDEN_NAME_PATTERNS.search(name) is None


def test_manifest_declares_physio_pose_and_surgery_scene() -> None:
    manifest = json.loads((VIDEO_DIR / "manifest.json").read_text(encoding="utf-8"))
    for key in MANIFEST_REQUIRED_KEYS:
        assert key in manifest, f"Chave ausente no manifest: {key}"

    by_file = {item["file"]: item for item in manifest["fixtures"]}
    assert set(by_file) == {"video_physio.avi", "video_surgery_light.avi"}

    for item in manifest["fixtures"]:
        for key in FIXTURE_REQUIRED_KEYS:
            assert key in item, f"Chave ausente em fixture: {key}"
        assert (VIDEO_DIR / item["file"]).is_file()
        assert item["width"] > 0 and item["height"] > 0
        assert item["frames"] >= 8

    assert by_file["video_physio.avi"]["scenario"] == "physio"
    assert by_file["video_physio.avi"]["analysis"] == "pose"
    assert by_file["video_surgery_light.avi"]["scenario"] == "surgery_light"
    assert by_file["video_surgery_light.avi"]["analysis"] == "scene"

    readme = (VIDEO_DIR / "README.md").read_text(encoding="utf-8")
    assert "3DYoga90" in readme or "3dyoga90" in readme.lower()
    assert "creativecommons" in readme.lower() or "CC " in readme or "CC0" in readme
    assert "prepare_video_fixtures" in readme
    assert "sangramento" not in readme.lower() or "sem" in readme.lower()


def test_prepare_video_fixtures_is_deterministic() -> None:
    assert PREPARE_SCRIPT.is_file()

    tracked = ("video_physio.avi", "video_surgery_light.avi", "manifest.json")
    before = {
        name: hashlib.sha256((VIDEO_DIR / name).read_bytes()).hexdigest()
        for name in tracked
    }

    result = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout

    after = {
        name: hashlib.sha256((VIDEO_DIR / name).read_bytes()).hexdigest()
        for name in tracked
    }
    assert before == after, "Regeneração das fixtures de vídeo não foi bit-a-bit estável"
