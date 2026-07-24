#!/usr/bin/env sh
# Evidência commitável de vídeo (Pose + Scene) — Épico 11 / T11.4.
#
# Uso:
#   ./scripts/gerar-evidencia-video.sh --dry-run   # CI / synthetic
#   ./scripts/gerar-evidencia-video.sh             # exige extras + backends reais
#
# Saída: data/evidencia/video/*.json
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      printf '%s\n' \
        'Gera evidência de vídeo em data/evidencia/video/.' \
        'Uso:' \
        '  ./scripts/gerar-evidencia-video.sh --dry-run' \
        '  ./scripts/gerar-evidencia-video.sh'
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
  printf 'Modo dry-run (engines synthetic)...\n'
else
  export LIMEN_POSE_BACKEND="${LIMEN_POSE_BACKEND:-mediapipe}"
  export LIMEN_YOLO_BACKEND="${LIMEN_YOLO_BACKEND:-ultralytics}"
  printf 'Modo video-live (POSE=%s YOLO=%s)...\n' \
    "$LIMEN_POSE_BACKEND" "$LIMEN_YOLO_BACKEND"
  printf 'Dica: uv sync --extra mediapipe --extra ultralytics (ou compose.video-real).\n'
fi

(cd backend && uv run python ../scripts/gerar_evidencia_video.py $EXTRA)
printf 'Pronto. Revise e commite data/evidencia/video/ se for evidência real.\n'
