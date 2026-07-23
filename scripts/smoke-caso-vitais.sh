#!/usr/bin/env sh
# Smoke Compose + Caso sintético só com vitais (Épico 8 / E8.1 / T8.1).
# Pré-requisito: AZURE_ENABLED=false (padrão do .env.example).
#
# Uso:
#   ./scripts/smoke-caso-vitais.sh           # sobe Compose (wait) + smoke HTTP
#   ./scripts/smoke-caso-vitais.sh --skip-up # assume stack já no ar
#
# Variáveis: ver scripts/smoke_caso_vitais.py (SEED_*, SMOKE_*, LIMEN_API_BASE).
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

SKIP_UP=0
for arg in "$@"; do
  case "$arg" in
    --skip-up) SKIP_UP=1 ;;
    -h|--help)
      printf '%s\n' \
        'Smoke Compose + Caso vitais até done (sem vídeo/áudio/Azure).' \
        'Uso:' \
        '  ./scripts/smoke-caso-vitais.sh           # up + smoke' \
        '  ./scripts/smoke-caso-vitais.sh --skip-up # só smoke HTTP' \
        'Requer AZURE_ENABLED=false no ambiente da stack.'
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

# Garante expectativa da spec no ambiente local do script.
export AZURE_ENABLED="${AZURE_ENABLED:-false}"
if [ "$AZURE_ENABLED" != "false" ] && [ "$AZURE_ENABLED" != "0" ]; then
  printf 'AVISO: AZURE_ENABLED=%s (spec E8.1 recomenda false).\n' "$AZURE_ENABLED" >&2
fi

WAIT_TIMEOUT="${SMOKE_WAIT_TIMEOUT_SECONDS:-300}"

if [ "$SKIP_UP" -eq 0 ]; then
  # Só serviços do caminho vitais (API + outbox + worker). Frontend não é necessário.
  printf 'Subindo stack smoke vitais (build + wait, timeout %ss)...\n' "$WAIT_TIMEOUT"
  docker compose up -d --build --wait --wait-timeout "$WAIT_TIMEOUT" \
    postgres redis minio minio-bootstrap backend worker outbox-reconciler
fi

printf 'Rodando smoke Caso vitais (HTTP)...\n'
if command -v uv >/dev/null 2>&1; then
  (cd backend && uv run python ../scripts/smoke_caso_vitais.py)
else
  python3 "$ROOT/scripts/smoke_caso_vitais.py"
fi

printf 'Smoke Caso vitais concluído com sucesso.\n'
