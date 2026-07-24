#!/usr/bin/env python3
"""CLI — evidência de áudio Azure (Épico 10 / T10.5).

Uso:
  # Dry-run (CI / sem chave): grava JSON sintético a partir do roteiro TTS
  cd backend && uv run python ../scripts/gerar_evidencia_audio.py --dry-run

  # Live (credenciais F0 no .env):
  AZURE_ENABLED=true cd backend && uv run python ../scripts/gerar_evidencia_audio.py

Prefira o wrapper: ./scripts/gerar-evidencia-audio.sh [--dry-run]
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

from app.evidencia.audio import run_evidencia_audio  # noqa: E402


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
    parser = argparse.ArgumentParser(description="Gera evidência de áudio (JSON).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Sem Azure: usa roteiro TTS + Sentimento sintético",
    )
    parser.add_argument(
        "--wav",
        type=Path,
        default=None,
        help="WAV de entrada (default: fixture TTS crítica)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Diretório de saída (default: data/evidencia/audio)",
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
        os.environ.setdefault("AZURE_ENABLED", "true")

    result = run_evidencia_audio(
        wav_path=args.wav,
        output_dir=args.out,
        dry_run=dry_run,
    )
    print(f"Evidência ({result.mode}) em {result.output_dir}")
    print(f"  - {result.analysis_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
