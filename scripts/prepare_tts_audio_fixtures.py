#!/usr/bin/env python3
"""Gera fixtures TTS pt-BR ≤60s (macOS `say` + `afconvert`) — Épico 10 / T10.5.

Produz:
  - audio_tts_neutra.wav
  - audio_tts_critica.wav  (Termos Críticos na fala)

Uso (macOS com voz Luciana):
    python scripts/prepare_tts_audio_fixtures.py

Fora do macOS: grave os roteiros abaixo como WAV 16 kHz mono e coloque em
data/fixtures/audio/tts/.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "fixtures" / "audio" / "tts"
CALIBRATION_VERSION = "2026-07-23.1"
SAMPLE_RATE = 16_000
VOICE = "Luciana"

ROTEIRO_NEUTRO = (
    "Bom dia, doutor. Estou me sentindo bem hoje. "
    "Dormi bem esta noite e não tenho nenhuma queixa importante. "
    "Continuo tomando os remédios como o senhor recomendou."
)

ROTEIRO_CRITICO = (
    "Doutor, não estou bem. Estou sentindo uma dor no peito muito forte "
    "e também estou com falta de ar desde ontem à noite. "
    "Tive uma tontura quando levantei e quase desmaiei."
)


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _say_to_wav(text: str, out: Path, *, rate: int = 180) -> None:
    aiff = out.with_suffix(".aiff")
    _run(["say", "-v", VOICE, "-r", str(rate), "-o", str(aiff), text])
    _run(
        [
            "afconvert",
            "-f",
            "WAVE",
            "-d",
            f"LEI16@{SAMPLE_RATE}",
            "-c",
            "1",
            str(aiff),
            str(out),
        ]
    )
    aiff.unlink(missing_ok=True)


def main() -> None:
    if sys.platform != "darwin" or shutil.which("say") is None:
        sys.exit(
            "Este gerador usa o TTS 'say' do macOS (voz Luciana). "
            "Em outros sistemas, grave ROTEIRO_NEUTRO / ROTEIRO_CRITICO "
            "como WAV 16 kHz mono em data/fixtures/audio/tts/."
        )
    if shutil.which("afconvert") is None:
        sys.exit("afconvert (macOS) é necessário para converter AIFF → WAV.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    neutra = OUTPUT_DIR / "audio_tts_neutra.wav"
    critica = OUTPUT_DIR / "audio_tts_critica.wav"
    print("Gerando audio_tts_neutra.wav ...")
    _say_to_wav(ROTEIRO_NEUTRO, neutra, rate=180)
    print("Gerando audio_tts_critica.wav ...")
    _say_to_wav(ROTEIRO_CRITICO, critica, rate=150)

    fixtures = []
    for path, scenario, script in (
        (neutra, "tts_neutra", ROTEIRO_NEUTRO),
        (critica, "tts_critica", ROTEIRO_CRITICO),
    ):
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        fixtures.append(
            {
                "file": path.name,
                "scenario": scenario,
                "sample_rate_hz": SAMPLE_RATE,
                "channels": 1,
                "bits": 16,
                "format": "wav_pcm_s16le",
                "sha256": sha,
                "script_pt_br": script,
                "notes": "TTS Luciana pt-BR ≤60s — demonstração, sem PHI.",
            }
        )
        print(f"  {path.name} sha256={sha} bytes={path.stat().st_size}")

    manifest = {
        "version": CALIBRATION_VERSION,
        "voice": VOICE,
        "generator": "scripts/prepare_tts_audio_fixtures.py",
        "fixtures": fixtures,
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Manifest em {OUTPUT_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()
