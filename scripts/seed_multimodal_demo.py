#!/usr/bin/env python3
"""Seed demo multimodal — in-memory (TDD) ou HTTP contra Compose (Épico 8 / T8.5).

Uso (na raiz do repo):

    # In-memory (sem Compose; smoke de contrato / TDD)
    cd backend && uv run python ../scripts/seed_multimodal_demo.py --memory

    # HTTP na stack Compose (demo real)
    ./scripts/seed-multimodal-demo.sh
    # ou:
    cd backend && uv run python ../scripts/seed_multimodal_demo.py --http

Variáveis (--http): LIMEN_API_BASE, SEED_MEDICO_*, BACKEND_PORT.
Idempotency-Key fixas: ver app.cases.multimodal_seed.
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

from app.cases.multimodal_seed import (  # noqa: E402
    DEMO_AUDIO_IDEMPOTENCY_KEY,
    DEMO_CASE_IDEMPOTENCY_KEY,
    DEMO_PRESCRIPTIONS_IDEMPOTENCY_KEY,
    DEMO_VIDEO_IDEMPOTENCY_KEY,
    seed_multimodal_demo,
)
from app.cases.multimodal_seed_http import (  # noqa: E402
    MultimodalSeedHttpConfig,
    MultimodalSeedHttpError,
    seed_multimodal_demo_http,
)
from app.cases.service import CaseService, InMemoryCaseStore  # noqa: E402
from app.cases.storage import InMemoryArtifactBlobStore  # noqa: E402
from app.outbox.service import (  # noqa: E402
    InMemoryOutboxStore,
    OutboxDispatcher,
    RecordingJobEnqueuer,
)
from app.patients.service import InMemoryPatientStore, PatientService  # noqa: E402


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def _run_memory() -> int:
    patient_store = InMemoryPatientStore()
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    patient_service = PatientService(store=patient_store, case_store=case_store)
    case_service = CaseService(
        store=case_store,
        patient_store=patient_store,
        blob_store=blob_store,
        outbox_dispatcher=OutboxDispatcher(
            store=InMemoryOutboxStore(),
            enqueuer=RecordingJobEnqueuer(),
        ),
    )
    first = seed_multimodal_demo(
        patient_service=patient_service,
        case_service=case_service,
    )
    second = seed_multimodal_demo(
        patient_service=patient_service,
        case_service=case_service,
    )
    case = case_service.get(first.case_id)
    modalities = sorted(m.modality for m in case.modalities)
    print("Seed multimodal demo (in-memory)")
    print(f"  patient_id={first.patient_id}")
    print(f"  case_id={first.case_id}")
    print(
        f"  created_case={first.created_case} replay_created_case={second.created_case}"
    )
    print(f"  modalities={modalities}")
    _print_keys()
    if second.case_id != first.case_id or second.created_case:
        print("ERROR: seed não foi idempotente", file=sys.stderr)
        return 1
    if modalities != ["audio", "prescriptions", "video", "vitals"]:
        print(f"ERROR: modalidades inesperadas: {modalities}", file=sys.stderr)
        return 1
    return 0


def _print_keys() -> None:
    print("  idempotency keys:")
    print(f"    vitals={DEMO_CASE_IDEMPOTENCY_KEY}")
    print(f"    video={DEMO_VIDEO_IDEMPOTENCY_KEY}")
    print(f"    audio={DEMO_AUDIO_IDEMPOTENCY_KEY}")
    print(f"    prescriptions={DEMO_PRESCRIPTIONS_IDEMPOTENCY_KEY}")


def _run_http() -> int:
    _load_dotenv(REPO_ROOT / ".env")
    port = os.getenv("BACKEND_PORT", "8000")
    base = os.getenv("LIMEN_API_BASE", f"http://127.0.0.1:{port}")
    azure = os.getenv("AZURE_ENABLED", "false")
    config = MultimodalSeedHttpConfig(
        base_url=base,
        username=os.getenv("SEED_MEDICO_USERNAME", "medico"),
        password=os.getenv("SEED_MEDICO_PASSWORD", "medico_dev_only"),
    )
    print(f"Seed multimodal demo (HTTP) → {config.base_url} (AZURE_ENABLED={azure})")
    try:
        first = seed_multimodal_demo_http(config)
        second = seed_multimodal_demo_http(config)
    except MultimodalSeedHttpError as exc:
        print(f"FALHA: {exc}", file=sys.stderr)
        return 1
    print(f"  patient_id={first.patient_id}")
    print(f"  case_id={first.case_id}")
    print(
        f"  created_case={first.created_case} replay_created_case={second.created_case}"
    )
    print(f"  modalities={list(first.modalities)}")
    _print_keys()
    if second.case_id != first.case_id or second.created_case:
        print("ERROR: seed HTTP não foi idempotente", file=sys.stderr)
        return 1
    print("OK — abra a UI em /casos/" + first.case_id)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed demo multimodal Limen")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--http",
        action="store_true",
        help="Seed via API HTTP (Compose no ar)",
    )
    mode.add_argument(
        "--memory",
        action="store_true",
        help="Seed in-memory (padrão se nenhum flag)",
    )
    args = parser.parse_args(argv)
    if args.http:
        return _run_http()
    return _run_memory()


if __name__ == "__main__":
    raise SystemExit(main())
