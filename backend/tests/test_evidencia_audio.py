"""TDD T10.5 — fixtures TTS + evidência de áudio (dry-run sem Azure)."""

from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from app.evidencia.audio import run_evidencia_audio

REPO_ROOT = Path(__file__).resolve().parents[2]
TTS_DIR = REPO_ROOT / "data" / "fixtures" / "audio" / "tts"
EVIDENCIA_DIR = REPO_ROOT / "data" / "evidencia" / "audio"
SCRIPT_AUDIO_SH = REPO_ROOT / "scripts" / "gerar-evidencia-audio.sh"
SCRIPT_REAL_SH = REPO_ROOT / "scripts" / "gerar-evidencia-real.sh"
SCRIPT_AUDIO_PY = REPO_ROOT / "scripts" / "gerar_evidencia_audio.py"
PREPARE_TTS = REPO_ROOT / "scripts" / "prepare_tts_audio_fixtures.py"

MAX_DURATION_SECONDS = 60.0
MAX_BYTES = 800_000


@pytest.mark.parametrize(
    "filename",
    ("audio_tts_neutra.wav", "audio_tts_critica.wav", "manifest.json", "README.md"),
)
def test_tts_fixture_files_exist(filename: str) -> None:
    assert (TTS_DIR / filename).is_file()


def test_tts_wavs_are_pcm_mono_under_60s() -> None:
    for name in ("audio_tts_neutra.wav", "audio_tts_critica.wav"):
        data = (TTS_DIR / name).read_bytes()
        assert len(data) <= MAX_BYTES
        assert data[:4] == b"RIFF"
        assert data[8:12] == b"WAVE"
        fmt_pos = data.find(b"fmt ")
        assert fmt_pos >= 0
        audio_format, channels, sample_rate, _, _, bits = struct.unpack_from(
            "<HHIIHH", data, fmt_pos + 8
        )
        assert audio_format == 1
        assert channels == 1
        assert sample_rate == 16_000
        assert bits == 16
        data_pos = data.find(b"data")
        data_size = struct.unpack_from("<I", data, data_pos + 4)[0]
        duration = data_size / (sample_rate * channels * (bits // 8))
        assert 0.5 <= duration <= MAX_DURATION_SECONDS


def test_tts_manifest_includes_scripts_and_sha() -> None:
    manifest = json.loads((TTS_DIR / "manifest.json").read_text(encoding="utf-8"))
    by_file = {item["file"]: item for item in manifest["fixtures"]}
    assert "audio_tts_critica.wav" in by_file
    critica = by_file["audio_tts_critica.wav"]
    assert "falta de ar" in critica["script_pt_br"].lower()
    assert "dor no peito" in critica["script_pt_br"].lower()
    assert PREPARE_TTS.is_file()


def test_evidencia_scripts_exist_and_orchestrator_delegates() -> None:
    assert SCRIPT_AUDIO_SH.is_file()
    assert SCRIPT_REAL_SH.is_file()
    assert SCRIPT_AUDIO_PY.is_file()
    real = SCRIPT_REAL_SH.read_text(encoding="utf-8")
    assert "gerar-evidencia-audio.sh" in real
    audio = SCRIPT_AUDIO_SH.read_text(encoding="utf-8")
    assert "gerar_evidencia_audio.py" in audio
    assert "data/evidencia/audio" in audio or "evidencia" in audio


def test_run_evidencia_audio_dry_run_writes_json(tmp_path: Path) -> None:
    out = tmp_path / "evidencia"
    result = run_evidencia_audio(
        wav_path=TTS_DIR / "audio_tts_critica.wav",
        output_dir=out,
        dry_run=True,
    )
    assert result.mode == "dry-run"
    assert result.analysis_path.is_file()

    analysis = json.loads(result.analysis_path.read_text(encoding="utf-8"))
    assert analysis["mode"] == "dry-run"
    assert analysis["transcript"]
    assert "falta de ar" in analysis["transcript"].lower()
    assert "falta de ar" in [t.lower() for t in analysis["critical_terms"]]
    assert analysis["sentiment"] == "negative"
    assert analysis["modality_risk"]["score"] >= 0.85
    assert (out / "transcript.json").is_file()
    assert (out / "sentiment.json").is_file()
    assert (out / "critical_terms.json").is_file()


def test_cli_dry_run_writes_under_tmp(tmp_path: Path) -> None:
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_AUDIO_PY),
            "--dry-run",
            "--wav",
            str(TTS_DIR / "audio_tts_critica.wav"),
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={
            **dict(**{k: v for k, v in __import__("os").environ.items()}),
            "PYTHONPATH": str(REPO_ROOT / "backend"),
        },
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert (out / "analysis.json").is_file()


def test_evidencia_readme_documents_scripts() -> None:
    readme = (EVIDENCIA_DIR / "README.md").read_text(encoding="utf-8")
    assert "gerar-evidencia-audio" in readme
    assert "dry-run" in readme.lower() or "--dry-run" in readme
