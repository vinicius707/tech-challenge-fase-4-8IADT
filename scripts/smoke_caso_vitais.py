#!/usr/bin/env python3
"""CLI do smoke Caso vitais (HTTP) — Épico 8 / T8.1.

Uso (stack Compose no ar, AZURE_ENABLED=false):

    ./scripts/smoke_caso_vitais.py
    LIMEN_API_BASE=http://127.0.0.1:8000 ./scripts/smoke_caso_vitais.py

Variáveis (opcionais; padrão = .env.example / seed local):

    LIMEN_API_BASE
    SEED_MEDICO_USERNAME / SEED_MEDICO_PASSWORD
    SMOKE_VITALS_FIXTURE   (default: data/fixtures/vitals/vitals_medium.csv)
    SMOKE_IDEMPOTENCY_KEY
    SMOKE_POLL_TIMEOUT_SECONDS
    SMOKE_POLL_INTERVAL_SECONDS
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.smoke.caso_vitais import (  # noqa: E402
    SmokeCasoVitaisConfig,
    SmokeCasoVitaisError,
    run_smoke_caso_vitais,
)


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


def main() -> int:
    _load_dotenv(REPO_ROOT / ".env")
    azure = os.getenv("AZURE_ENABLED", "false").strip().lower()
    if azure in {"1", "true", "yes", "on"}:
        print(
            "AVISO: AZURE_ENABLED está ligado; o smoke de entrega espera false "
            "(spec E8.1). Continuando mesmo assim.",
            file=sys.stderr,
        )

    fixture = Path(
        os.getenv(
            "SMOKE_VITALS_FIXTURE",
            str(REPO_ROOT / "data" / "fixtures" / "vitals" / "vitals_medium.csv"),
        )
    )
    if not fixture.is_absolute():
        fixture = REPO_ROOT / fixture

    port = os.getenv("BACKEND_PORT", "8000")
    base = os.getenv("LIMEN_API_BASE", f"http://127.0.0.1:{port}")
    config = SmokeCasoVitaisConfig(
        base_url=base,
        username=os.getenv("SEED_MEDICO_USERNAME", "medico"),
        password=os.getenv("SEED_MEDICO_PASSWORD", "medico_dev_only"),
        vitals_csv_path=fixture,
        idempotency_key=os.getenv("SMOKE_IDEMPOTENCY_KEY", "smoke-caso-vitais"),
        poll_timeout_seconds=float(os.getenv("SMOKE_POLL_TIMEOUT_SECONDS", "120")),
        poll_interval_seconds=float(os.getenv("SMOKE_POLL_INTERVAL_SECONDS", "1")),
    )

    print(f"Smoke Caso vitais → {config.base_url} (AZURE_ENABLED={azure or 'false'})")
    try:
        result = run_smoke_caso_vitais(config)
    except SmokeCasoVitaisError as exc:
        print(f"FALHA: {exc}", file=sys.stderr)
        return 1
    print(
        f"OK Caso {result.case_id} patient={result.patient_id} status={result.status}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
