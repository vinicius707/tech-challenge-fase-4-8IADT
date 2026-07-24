#!/usr/bin/env sh
# Orquestrador fino de evidência IA real (ADR 0030) — Épico 10.
# Nesta entrega só delega ao script de áudio; Épicos 11/9 acrescentam etapas.
#
# Uso:
#   ./scripts/gerar-evidencia-real.sh --dry-run
#   ./scripts/gerar-evidencia-real.sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

printf '=== Evidência real: áudio (Épico 10) ===\n'
./scripts/gerar-evidencia-audio.sh "$@"
printf '=== Orquestrador E10 concluído (vídeo/vitals ML: épicos seguintes) ===\n'
