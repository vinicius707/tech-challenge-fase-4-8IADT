#!/usr/bin/env python3
"""Gera fixtures sintéticas de áudio (WAV PCM S16LE) — reprodutível, sem download.

Clips mínimos para TDD/demo da modalidade `audio` (Épico 6 / E6.2).
Fontes públicas de referência (AudioSet, Medical Speech) ficam documentadas
no README; brutos grandes não entram no Git nem no CI.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "fixtures" / "audio"

CALIBRATION_VERSION = "2026-07-21.1"
SEED = 20260721
SAMPLE_RATE = 8000
CHANNELS = 1
BITS = 16
DURATION_SECONDS = 2.0  # ≤60s; curto para Git/CI


def _u16(value: int) -> bytes:
    return struct.pack("<H", value)


def _u32(value: int) -> bytes:
    return struct.pack("<I", value)


def _pcm_s16le_tone(*, sample_rate: int, duration: float, seed: int) -> bytes:
    """Tom + envelope determinísticos (proxy de utterance — sem fala real)."""
    n = int(sample_rate * duration)
    # Frequências derivadas do seed (sem random não-determinístico).
    f1 = 220 + (seed % 97)
    f2 = 330 + (seed % 53)
    out = bytearray()
    for i in range(n):
        t = i / sample_rate
        # Envelope suave (ataque/decay) — evita click.
        env = min(1.0, t * 8.0) * min(1.0, (duration - t) * 8.0)
        sample = 0.45 * math.sin(2 * math.pi * f1 * t) + 0.25 * math.sin(
            2 * math.pi * f2 * t
        )
        # Harmônico leve indexado pelo seed.
        sample += 0.08 * math.sin(2 * math.pi * (f1 * 2) * t + (seed % 7) * 0.1)
        value = int(max(-1.0, min(1.0, sample * env)) * 32767)
        out.extend(struct.pack("<h", value))
    return bytes(out)


def write_wav(path: Path, pcm: bytes, *, sample_rate: int = SAMPLE_RATE) -> None:
    byte_rate = sample_rate * CHANNELS * (BITS // 8)
    block_align = CHANNELS * (BITS // 8)
    data_size = len(pcm)
    fmt = (
        _u16(1)  # PCM
        + _u16(CHANNELS)
        + _u32(sample_rate)
        + _u32(byte_rate)
        + _u16(block_align)
        + _u16(BITS)
    )
    riff_size = 4 + (8 + len(fmt)) + (8 + data_size)
    path.write_bytes(
        b"RIFF"
        + _u32(riff_size)
        + b"WAVE"
        + b"fmt "
        + _u32(len(fmt))
        + fmt
        + b"data"
        + _u32(data_size)
        + pcm
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pcm = _pcm_s16le_tone(
        sample_rate=SAMPLE_RATE, duration=DURATION_SECONDS, seed=SEED
    )
    wav_path = OUTPUT_DIR / "audio_speech.wav"
    write_wav(wav_path, pcm)
    sha = hashlib.sha256(wav_path.read_bytes()).hexdigest()

    manifest = {
        "version": CALIBRATION_VERSION,
        "seed": SEED,
        "fixtures": [
            {
                "file": "audio_speech.wav",
                "scenario": "speech",
                "sample_rate_hz": SAMPLE_RATE,
                "channels": CHANNELS,
                "bits": BITS,
                "duration_seconds": DURATION_SECONDS,
                "format": "wav_pcm_s16le",
                "sha256": sha,
                "notes": (
                    "Tom sintético ≤60s — proxy de utterance/Medical Speech; "
                    "sem PHI nem diagnóstico."
                ),
            }
        ],
        "reference_sources": {
            "speech": "https://research.google.com/audioset/ (referência; brutos fora do Git)",
            "medical_speech_cc": (
                "Gravação própria / material CC ≤60s — URL concreta no README"
            ),
        },
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {wav_path.name} ({len(wav_path.read_bytes())} bytes) sha256={sha}")


if __name__ == "__main__":
    main()
