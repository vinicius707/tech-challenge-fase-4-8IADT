#!/usr/bin/env sh
# Evidência commitável de áudio (Speech + Language + Termos) — Épico 10 / T10.5.
#
# Uso:
#   ./scripts/gerar-evidencia-audio.sh --dry-run   # CI / sem chave Azure
#   ./scripts/gerar-evidencia-audio.sh             # exige AZURE_* no .env
#
# Saída: data/evidencia/audio/*.json
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      printf '%s\n' \
        'Gera evidência de áudio em data/evidencia/audio/.' \
        'Uso:' \
        '  ./scripts/gerar-evidencia-audio.sh --dry-run' \
        '  ./scripts/gerar-evidencia-audio.sh'
      exit 0
      ;;
    *)
      printf 'Argumento desconhecido: %s\n' "$arg" >&2
      exit 2
      ;;
  esac
done

if [ ! -f .env ]; then
  printf 'Criando .env a partir de .env.example...\n'
  cp .env.example .env
fi

# shellcheck disable=SC1091
set -a
. ./.env
set +a

EXTRA=""
if [ "$DRY_RUN" -eq 1 ] || [ "${LIMEN_EVIDENCIA_DRY_RUN:-}" = "true" ] \
  || [ "${LIMEN_EVIDENCIA_DRY_RUN:-}" = "1" ]; then
  EXTRA="--dry-run"
  printf 'Modo dry-run (sem chamada Azure)...\n'
else
  export AZURE_ENABLED="${AZURE_ENABLED:-true}"
  if [ -z "${AZURE_SPEECH_KEY:-}" ] || [ -z "${AZURE_SPEECH_REGION:-}" ]; then
    printf 'Defina AZURE_SPEECH_KEY e AZURE_SPEECH_REGION no .env (ou use --dry-run).\n' >&2
    exit 1
  fi
  printf 'Modo Azure live (AZURE_ENABLED=%s)...\n' "$AZURE_ENABLED"
fi

(cd backend && uv run python ../scripts/gerar_evidencia_audio.py $EXTRA)
printf 'Pronto. Revise e commite data/evidencia/audio/ se for evidência real.\n'
