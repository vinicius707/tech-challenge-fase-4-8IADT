"""TDD T6.8 — contrato das fixtures de áudio (spec epic-06 E6.2)."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIO_DIR = REPO_ROOT / "data" / "fixtures" / "audio"
PREPARE_SCRIPT = REPO_ROOT / "scripts" / "prepare_audio_fixtures.py"

REQUIRED_FILES = (
    "audio_speech.wav",
    "manifest.json",
    "README.md",
)

MANIFEST_REQUIRED_KEYS = ("version", "seed", "fixtures")
FIXTURE_REQUIRED_KEYS = (
    "file",
    "scenario",
    "sample_rate_hz",
    "channels",
    "duration_seconds",
    "format",
)

FORBIDDEN_NAME_PATTERNS = re.compile(
    r"(cpf|prontuario|patient_id|ssn|diagnostico|diagnosis)",
    re.IGNORECASE,
)

# Limite frouxo para Git (≤60s PCM mono 8 kHz ≈ 1 MB; fixture bem menor).
MAX_BYTES_PER_CLIP = 250_000
MAX_DURATION_SECONDS = 60.0


@pytest.mark.parametrize("filename", REQUIRED_FILES)
def test_audio_fixture_file_exists(filename: str) -> None:
    path = AUDIO_DIR / filename
    assert path.is_file(), f"Fixture ausente: {path}"


def test_audio_clip_is_wav_pcm_short_and_small() -> None:
    path = AUDIO_DIR / "audio_speech.wav"
    data = path.read_bytes()
    assert len(data) > 44, "WAV vazio demais"
    assert len(data) <= MAX_BYTES_PER_CLIP, "Clip grande demais para Git"
    assert data[:4] == b"RIFF", "Não é RIFF"
    assert data[8:12] == b"WAVE", "Não é WAVE"
    assert FORBIDDEN_NAME_PATTERNS.search(path.name) is None

    # fmt chunk: audio_format=1 (PCM), channels, sample_rate
    fmt_pos = data.find(b"fmt ")
    assert fmt_pos >= 0
    audio_format, channels, sample_rate, _, _, bits = struct.unpack_from(
        "<HHIIHH", data, fmt_pos + 8
    )
    assert audio_format == 1, "Espera PCM"
    assert channels == 1
    assert sample_rate >= 8000
    assert bits == 16

    data_pos = data.find(b"data")
    assert data_pos >= 0
    data_size = struct.unpack_from("<I", data, data_pos + 4)[0]
    duration = data_size / (sample_rate * channels * (bits // 8))
    assert 0.5 <= duration <= MAX_DURATION_SECONDS


def test_manifest_declares_speech_fixture_and_sources() -> None:
    manifest = json.loads((AUDIO_DIR / "manifest.json").read_text(encoding="utf-8"))
    for key in MANIFEST_REQUIRED_KEYS:
        assert key in manifest, f"Chave ausente no manifest: {key}"

    by_file = {item["file"]: item for item in manifest["fixtures"]}
    assert "audio_speech.wav" in by_file

    item = by_file["audio_speech.wav"]
    for key in FIXTURE_REQUIRED_KEYS:
        assert key in item, f"Chave ausente em fixture: {key}"
    assert (AUDIO_DIR / item["file"]).is_file()
    assert item["scenario"] == "speech"
    assert item["duration_seconds"] <= MAX_DURATION_SECONDS
    assert item["format"] == "wav_pcm_s16le"
    assert item["sample_rate_hz"] >= 8000
    assert item["channels"] == 1

    readme = (AUDIO_DIR / "README.md").read_text(encoding="utf-8")
    assert "audioset" in readme.lower()
    assert "prepare_audio_fixtures" in readme
    assert "60" in readme  # ≤60s documentado


def test_prepare_audio_fixtures_is_deterministic() -> None:
    assert PREPARE_SCRIPT.is_file()

    tracked = ("audio_speech.wav", "manifest.json")
    before = {
        name: hashlib.sha256((AUDIO_DIR / name).read_bytes()).hexdigest()
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
        name: hashlib.sha256((AUDIO_DIR / name).read_bytes()).hexdigest()
        for name in tracked
    }
    assert before == after, "Regeneração das fixtures de áudio não foi bit-a-bit estável"
