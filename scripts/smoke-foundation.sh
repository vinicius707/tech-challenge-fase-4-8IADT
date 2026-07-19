#!/bin/sh
set -eu

wait_timeout="${SMOKE_WAIT_TIMEOUT_SECONDS:-120}"

printf 'Subindo a stack Limen...\n'
docker compose up -d --build --wait --wait-timeout "$wait_timeout"

printf 'Validando GET /health...\n'
docker compose exec -T backend python - <<'PY'
import json
import urllib.request

expected = {
    "status": "ok",
    "checks": {
        "postgres": "ok",
        "redis": "ok",
        "minio": "ok",
    },
}

with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5) as response:
    body = json.load(response)
    if response.status != 200:
        raise SystemExit(f"/health retornou HTTP {response.status}")
    if body != expected:
        raise SystemExit(f"Contrato inesperado de /health: {body!r}")
PY

printf 'Validando bucket MinIO...\n'
docker compose run --rm --no-deps --entrypoint /bin/sh minio-bootstrap -c '
  mc alias set limen-local http://minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null
  mc stat "limen-local/$MINIO_BUCKET" >/dev/null
'

printf 'Validando revisão Alembic...\n'
docker compose exec -T backend alembic current --check-heads >/dev/null

printf 'Smoke da fundação concluído com sucesso.\n'
