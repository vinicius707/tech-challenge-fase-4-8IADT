#!/usr/bin/env sh
# Sobe a aplicação Limen completa (Compose) e valida health + UI.
# Uso:
#   ./scripts/start-limen.sh           # sobe e espera healthy
#   ./scripts/start-limen.sh --smoke   # sobe + smoke da fundação
#   ./scripts/start-limen.sh --down    # encerra (mantém volumes)
#   ./scripts/start-limen.sh --reset   # encerra e apaga volumes
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

WAIT_TIMEOUT="${LIMEN_WAIT_TIMEOUT_SECONDS:-300}"
MODE="up"

for arg in "$@"; do
  case "$arg" in
    --smoke) MODE="smoke" ;;
    --down) MODE="down" ;;
    --reset) MODE="reset" ;;
    -h|--help)
      printf '%s\n' \
        'Sobe a aplicação Limen completa (Compose) e valida health + UI.' \
        'Uso:' \
        '  ./scripts/start-limen.sh           # sobe e espera healthy' \
        '  ./scripts/start-limen.sh --smoke   # sobe + smoke da fundação' \
        '  ./scripts/start-limen.sh --down    # encerra (mantém volumes)' \
        '  ./scripts/start-limen.sh --reset   # encerra e apaga volumes'
      exit 0
      ;;
    *)
      printf 'Argumento desconhecido: %s\n' "$arg" >&2
      exit 2
      ;;
  esac
done

ensure_env() {
  if [ ! -f .env ]; then
    printf 'Criando .env a partir de .env.example...\n'
    cp .env.example .env
  fi
}

wait_http() {
  url="$1"
  label="$2"
  tries="${3:-60}"
  i=0
  while [ "$i" -lt "$tries" ]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      printf 'OK  %s (%s)\n' "$label" "$url"
      return 0
    fi
    i=$((i + 1))
    sleep 2
  done
  printf 'Falha ao aguardar %s (%s)\n' "$label" "$url" >&2
  return 1
}

print_banner() {
  printf '\n'
  printf 'Limen no ar\n'
  printf '===========\n'
  printf '  UI ........ http://localhost:%s\n' "${FRONTEND_PORT:-3000}"
  printf '  API ....... http://localhost:%s\n' "${BACKEND_PORT:-8000}"
  printf '  API/UI .... http://localhost:%s/api/health\n' "${FRONTEND_PORT:-3000}"
  printf '  OpenAPI ... http://localhost:%s/docs\n' "${BACKEND_PORT:-8000}"
  printf '  MinIO ..... http://localhost:%s\n' "${MINIO_CONSOLE_PORT:-9001}"
  printf '\n'
  printf 'Login demo (seed do .env.example):\n'
  printf '  usuario: medico   senha: medico_dev_only\n'
  printf '  usuario: admin    senha: admin_dev_only\n'
  printf '\n'
  printf 'Encerrar: ./scripts/start-limen.sh --down\n'
  printf 'Guia UI:  docs/frontend/guia-de-uso.md\n'
  printf '\n'
}

case "$MODE" in
  down)
    ensure_env
    # shellcheck disable=SC1091
    set -a
    [ -f .env ] && . ./.env
    set +a
    printf 'Encerrando stack (volumes preservados)...\n'
    docker compose down
    printf 'Stack encerrada.\n'
    exit 0
    ;;
  reset)
    ensure_env
    printf 'Encerrando stack e apagando volumes (Postgres/MinIO)...\n'
    docker compose down -v
    printf 'Stack e volumes removidos.\n'
    exit 0
    ;;
esac

ensure_env
# shellcheck disable=SC1091
set -a
. ./.env
set +a

printf 'Subindo Limen (build + wait, timeout %ss)...\n' "$WAIT_TIMEOUT"
docker compose up -d --build --wait --wait-timeout "$WAIT_TIMEOUT"

printf 'Validando endpoints...\n'
wait_http "http://127.0.0.1:${BACKEND_PORT:-8000}/health" "API /health"
wait_http "http://127.0.0.1:${FRONTEND_PORT:-3000}/api/health" "UI proxy /api/health"
wait_http "http://127.0.0.1:${FRONTEND_PORT:-3000}/login" "UI /login"

if [ "$MODE" = "smoke" ]; then
  printf 'Rodando smoke da fundação...\n'
  SMOKE_WAIT_TIMEOUT_SECONDS=30 ./scripts/smoke-foundation.sh
fi

print_banner
