#!/usr/bin/env sh
# Seed demo multimodal via HTTP na stack Compose (Épico 8 / E8.2 / T8.5).
#
# Pré-requisito: stack no ar (./scripts/start-limen.sh) com SEED_* e
# AZURE_ENABLED=false no .env.
#
# Ordem da demo: up → seed → UI/API
#
# Uso:
#   ./scripts/seed-multimodal-demo.sh
#   LIMEN_API_BASE=http://127.0.0.1:8000 ./scripts/seed-multimodal-demo.sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  printf 'Criando .env a partir de .env.example...\n'
  cp .env.example .env
fi

# shellcheck disable=SC1091
set -a
. ./.env
set +a

export AZURE_ENABLED="${AZURE_ENABLED:-false}"

printf 'Seed multimodal (HTTP) — AZURE_ENABLED=%s\n' "$AZURE_ENABLED"
if command -v uv >/dev/null 2>&1; then
  (cd backend && uv run python ../scripts/seed_multimodal_demo.py --http)
else
  python3 "$ROOT/scripts/seed_multimodal_demo.py" --http
fi
