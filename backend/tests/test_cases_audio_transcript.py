"""TDD T10.4 — Artefato de Transcrição real no MinIO (text/plain)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.azure.provider import clear_audio_analysis_cache
from app.cases import runtime as runtime_mod
from app.cases.processing import process_modality_for_case
from app.cases.service import (
    ArtifactRecord,
    CaseRecord,
    InMemoryCaseStore,
    ModalityRecord,
)
from app.cases.storage import InMemoryArtifactBlobStore
from app.outbox import completion as completion_mod

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIO_SPEECH = (
    REPO_ROOT / "data" / "fixtures" / "audio" / "audio_speech.wav"
).read_bytes()


@pytest.fixture(autouse=True)
def reset_runtime_and_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    clear_audio_analysis_cache()
    monkeypatch.delenv("LIMEN_FORCE_FAIL_MODALITIES", raising=False)
    monkeypatch.setenv("AZURE_ENABLED", "false")
    yield
    clear_audio_analysis_cache()
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def _seed_audio_case(
    *,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
) -> uuid.UUID:
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    object_key = f"cases/{case_id}/audio/audio_speech.wav"
    blob_store.put(
        bucket="limen",
        object_key=object_key,
        content=AUDIO_SPEECH,
        content_type="audio/wav",
    )
    case_store.save(
        CaseRecord(
            id=case_id,
            patient_id=uuid.uuid4(),
            status="pending",
            risk_score=None,
            risk_level=None,
            idempotency_key=str(uuid.uuid4()),
            content_sha256="x",
            created_at=now,
            updated_at=now,
            modalities=[
                ModalityRecord(
                    id=uuid.uuid4(),
                    case_id=case_id,
                    modality="audio",
                    status="pending",
                    artifact_id=artifact_id,
                    created_at=now,
                    updated_at=now,
                )
            ],
            artifacts=[
                ArtifactRecord(
                    id=artifact_id,
                    case_id=case_id,
                    modality="audio",
                    bucket="limen",
                    object_key=object_key,
                    content_sha256="x",
                    content_type="audio/wav",
                    created_at=now,
                )
            ],
        )
    )
    return case_id


def test_local_audio_does_not_persist_transcript_artifact() -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_audio_case(case_store=case_store, blob_store=blob_store)
    runtime_mod.configure_case_runtime(case_store, blob_store)

    result = process_modality_for_case(case_id, "audio")
    assert result is not None
    transcripts = [a for a in result.artifacts if a.modality == "audio_transcript"]
    assert transcripts == []
    assert (
        blob_store.get("limen", f"cases/{case_id}/audio/transcript.txt") is None
    )


def test_real_transcript_persists_text_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_audio_case(case_store=case_store, blob_store=blob_store)
    runtime_mod.configure_case_runtime(case_store, blob_store)

    monkeypatch.setenv("AZURE_ENABLED", "true")
    monkeypatch.setattr(
        "app.azure.provider.default_azure_analyze",
        lambda _payload: {
            "transcript": "paciente com falta de ar",
            "score": 0.25,
        },
    )

    result = process_modality_for_case(case_id, "audio")
    assert result is not None

    audio_mod = next(m for m in result.modalities if m.modality == "audio")
    assert audio_mod.status == "done"
    assert audio_mod.provider == "azure"

    transcripts = [a for a in result.artifacts if a.modality == "audio_transcript"]
    assert len(transcripts) == 1
    art = transcripts[0]
    assert art.object_key == f"cases/{case_id}/audio/transcript.txt"
    assert art.content_type == "text/plain"
    expected = b"paciente com falta de ar"
    assert art.content_sha256 == hashlib.sha256(expected).hexdigest()
    assert blob_store.get(art.bucket, art.object_key) == expected

    # Modalidade audio continua apontando para o WAV.
    wav = next(a for a in result.artifacts if a.modality == "audio")
    assert audio_mod.artifact_id == wav.id
    assert wav.content_type == "audio/wav"
