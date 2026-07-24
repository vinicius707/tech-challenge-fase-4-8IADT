#!/usr/bin/env sh
# Orquestrador fino de evidência IA real (ADR 0030) — Épicos 10 + 11.
# Delega a áudio e vídeo; Épico 9 (vitais ML) acrescenta etapas depois.
#
# Uso:
#   ./scripts/gerar-evidencia-real.sh --dry-run
#   ./scripts/gerar-evidencia-real.sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

printf '=== Evidência real: áudio (Épico 10) ===\n'
./scripts/gerar-evidencia-audio.sh "$@"
printf '=== Evidência real: vídeo (Épico 11) ===\n'
./scripts/gerar-evidencia-video.sh "$@"
printf '=== Orquestrador E10+E11 concluído (vitals ML: Épico 9) ===\n'
