"""Seed demo multimodal — Paciente + Caso com vitals/vídeo/áudio/prescriptions.

Determinístico via `Idempotency-Key` fixas (Épico 6 / T6.19). Sem UI; sem
Azure real. Seed completo de entrega / notebooks = Épico 8.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from app.cases.service import CaseService
from app.patients.service import PatientService

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPO_ROOT / "data" / "fixtures"

DEMO_CASE_IDEMPOTENCY_KEY = "limen-demo-multimodal-vitals-v1"
DEMO_VIDEO_IDEMPOTENCY_KEY = "limen-demo-multimodal-video-v1"
DEMO_AUDIO_IDEMPOTENCY_KEY = "limen-demo-multimodal-audio-v1"
DEMO_PRESCRIPTIONS_IDEMPOTENCY_KEY = "limen-demo-multimodal-prescriptions-v1"

_VITALS = FIXTURES / "vitals" / "vitals_medium.csv"
_VIDEO = FIXTURES / "video" / "video_physio.avi"
_AUDIO = FIXTURES / "audio" / "audio_speech.wav"
_RX = FIXTURES / "prescriptions" / "prescriptions_normal.csv"


@dataclass(frozen=True)
class MultimodalSeedResult:
    patient_id: uuid.UUID
    case_id: uuid.UUID
    created_case: bool
    created_video: bool
    created_audio: bool
    created_prescriptions: bool


def seed_multimodal_demo(
    *,
    patient_service: PatientService,
    case_service: CaseService,
) -> MultimodalSeedResult:
    """Cria (ou reutiliza) um Caso demo com as quatro modalidades anexadas."""
    existing = case_service.get_by_idempotency_key(DEMO_CASE_IDEMPOTENCY_KEY)
    if existing is not None:
        patient_id = existing.patient_id
        case_id = existing.id
        created_case = False
    else:
        patient = patient_service.create()
        patient_id = patient.id
        case, created_case = case_service.create(
            patient_id=patient_id,
            idempotency_key=DEMO_CASE_IDEMPOTENCY_KEY,
            content=_VITALS.read_bytes(),
            content_type="text/csv",
            filename="vitals_medium.csv",
        )
        case_id = case.id

    _, created_video = case_service.attach_video(
        case_id,
        idempotency_key=DEMO_VIDEO_IDEMPOTENCY_KEY,
        content=_VIDEO.read_bytes(),
        content_type="video/x-msvideo",
        filename="video_physio.avi",
    )
    _, created_audio = case_service.attach_audio(
        case_id,
        idempotency_key=DEMO_AUDIO_IDEMPOTENCY_KEY,
        content=_AUDIO.read_bytes(),
        content_type="audio/wav",
        filename="audio_speech.wav",
    )
    _, created_prescriptions = case_service.attach_prescriptions(
        case_id,
        idempotency_key=DEMO_PRESCRIPTIONS_IDEMPOTENCY_KEY,
        content=_RX.read_bytes(),
        content_type="text/csv",
        filename="prescriptions_normal.csv",
    )
    return MultimodalSeedResult(
        patient_id=patient_id,
        case_id=case_id,
        created_case=created_case,
        created_video=created_video,
        created_audio=created_audio,
        created_prescriptions=created_prescriptions,
    )
