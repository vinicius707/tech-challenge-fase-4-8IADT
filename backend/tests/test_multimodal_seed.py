"""TDD T6.19 — seed demo multimodal (vitals+vídeo+áudio+prescriptions)."""

from __future__ import annotations

from app.cases.multimodal_seed import (
    DEMO_AUDIO_IDEMPOTENCY_KEY,
    DEMO_CASE_IDEMPOTENCY_KEY,
    DEMO_PRESCRIPTIONS_IDEMPOTENCY_KEY,
    DEMO_VIDEO_IDEMPOTENCY_KEY,
    seed_multimodal_demo,
)
from app.cases.service import CaseService, InMemoryCaseStore
from app.cases.storage import InMemoryArtifactBlobStore
from app.outbox.service import InMemoryOutboxStore, OutboxDispatcher, RecordingJobEnqueuer
from app.patients.service import InMemoryPatientStore, PatientService


def _services() -> tuple[PatientService, CaseService, InMemoryCaseStore, InMemoryArtifactBlobStore]:
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
    return patient_service, case_service, case_store, blob_store


def test_seed_multimodal_creates_case_with_four_modality_artifacts() -> None:
    patient_service, case_service, _case_store, blob_store = _services()
    result = seed_multimodal_demo(
        patient_service=patient_service,
        case_service=case_service,
    )
    assert result.created_case is True
    body = case_service.get(result.case_id)
    modalities = {m.modality for m in body.modalities}
    assert modalities == {"vitals", "video", "audio", "prescriptions"}
    assert all(m.status == "pending" for m in body.modalities)

    arts = {a.modality: a for a in body.artifacts}
    assert set(arts) == {"vitals", "video", "audio", "prescriptions"}
    for art in arts.values():
        assert blob_store.get(art.bucket, art.object_key) is not None
        assert len(blob_store.get(art.bucket, art.object_key) or b"") > 0


def test_seed_multimodal_is_idempotent_on_replay() -> None:
    patient_service, case_service, case_store, _blob = _services()
    first = seed_multimodal_demo(
        patient_service=patient_service,
        case_service=case_service,
    )
    second = seed_multimodal_demo(
        patient_service=patient_service,
        case_service=case_service,
    )
    assert first.case_id == second.case_id
    assert second.created_case is False
    assert case_store.get_by_idempotency_key(DEMO_CASE_IDEMPOTENCY_KEY) is not None
    assert case_store.get_by_video_idempotency_key(DEMO_VIDEO_IDEMPOTENCY_KEY) is not None
    assert case_store.get_by_audio_idempotency_key(DEMO_AUDIO_IDEMPOTENCY_KEY) is not None
    assert (
        case_store.get_by_prescriptions_idempotency_key(
            DEMO_PRESCRIPTIONS_IDEMPOTENCY_KEY
        )
        is not None
    )
    # Um único Caso demo (não duplica modalidades).
    cases = case_store.list_by_patient(first.patient_id)
    assert len(cases) == 1
    assert len(cases[0].modalities) == 4


def test_seed_multimodal_uses_documented_idempotency_keys() -> None:
    assert DEMO_CASE_IDEMPOTENCY_KEY.startswith("limen-demo-multimodal-")
    assert DEMO_VIDEO_IDEMPOTENCY_KEY.startswith("limen-demo-multimodal-")
    assert DEMO_AUDIO_IDEMPOTENCY_KEY.startswith("limen-demo-multimodal-")
    assert DEMO_PRESCRIPTIONS_IDEMPOTENCY_KEY.startswith("limen-demo-multimodal-")
