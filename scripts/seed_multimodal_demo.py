#!/usr/bin/env python3
"""Seed demo multimodal (vitals + vídeo + áudio + prescriptions) — smoke local.

Por padrão usa stores in-memory (TDD/demo sem Compose). Para a stack real,
use a API HTTP com as mesmas Idempotency-Key (ver README do script / spec E6.3).

Uso (na raiz do repo):

    cd backend && uv run python ../scripts/seed_multimodal_demo.py
"""

from __future__ import annotations

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
from app.cases.service import CaseService, InMemoryCaseStore  # noqa: E402
from app.cases.storage import InMemoryArtifactBlobStore  # noqa: E402
from app.outbox.service import (  # noqa: E402
    InMemoryOutboxStore,
    OutboxDispatcher,
    RecordingJobEnqueuer,
)
from app.patients.service import InMemoryPatientStore, PatientService  # noqa: E402


def main() -> int:
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
    print(f"  created_case={first.created_case} replay_created_case={second.created_case}")
    print(f"  modalities={modalities}")
    print("  idempotency keys:")
    print(f"    vitals={DEMO_CASE_IDEMPOTENCY_KEY}")
    print(f"    video={DEMO_VIDEO_IDEMPOTENCY_KEY}")
    print(f"    audio={DEMO_AUDIO_IDEMPOTENCY_KEY}")
    print(f"    prescriptions={DEMO_PRESCRIPTIONS_IDEMPOTENCY_KEY}")
    if second.case_id != first.case_id or second.created_case:
        print("ERROR: seed não foi idempotente", file=sys.stderr)
        return 1
    if modalities != ["audio", "prescriptions", "video", "vitals"]:
        print(f"ERROR: modalidades inesperadas: {modalities}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
