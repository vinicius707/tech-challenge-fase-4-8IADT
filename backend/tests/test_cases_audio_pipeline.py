"""TDD T6.10 — analyzer local + cache SHA-256 + Azure injetável no pipeline."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.azure.circuit_breaker import AzureCircuitBreaker
from app.azure.provider import (
    analyze_audio,
    clear_audio_analysis_cache,
    default_local_analyze,
)
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


def test_local_analyze_fixture_returns_transcript_and_score() -> None:
    data = default_local_analyze(AUDIO_SPEECH)
    assert data["transcript"]
    assert 0.0 <= float(data["score"]) <= 1.0


def test_analyze_audio_local_when_azure_disabled() -> None:
    result = analyze_audio(AUDIO_SPEECH, azure_enabled=False)
    assert result.provider == "local"
    assert result.transcript
    assert result.score >= 0.0


def test_analyze_audio_cache_hit_skips_azure_callable() -> None:
    calls: list[str] = []

    def fake_azure(_payload: bytes) -> dict[str, object]:
        calls.append("azure")
        return {"transcript": "from-azure", "score": 0.22}

    first = analyze_audio(
        AUDIO_SPEECH,
        azure_enabled=True,
        azure_analyze=fake_azure,
        circuit_breaker=AzureCircuitBreaker(failure_threshold=3, open_seconds=60),
    )
    assert first.provider == "azure"
    assert calls == ["azure"]

    second = analyze_audio(
        AUDIO_SPEECH,
        azure_enabled=True,
        azure_analyze=fake_azure,
        circuit_breaker=AzureCircuitBreaker(failure_threshold=3, open_seconds=60),
    )
    assert second.provider == "cache"
    assert second.transcript == first.transcript
    assert second.score == first.score
    assert calls == ["azure"], "cache não deve chamar Azure de novo"


def test_analyze_audio_azure_failure_falls_back_local_and_records_cb() -> None:
    cb = AzureCircuitBreaker(failure_threshold=3, open_seconds=60)

    def flaky(_payload: bytes) -> dict[str, object]:
        raise ConnectionError("quota")

    result = analyze_audio(
        AUDIO_SPEECH,
        circuit_breaker=cb,
        azure_enabled=True,
        azure_analyze=flaky,
    )
    assert result.provider == "local"
    assert result.transcript
    assert cb.failure_count == 1


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


def test_process_audio_local_marks_done_and_fuses_risk() -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_audio_case(case_store=case_store, blob_store=blob_store)
    runtime_mod.configure_case_runtime(case_store, blob_store)

    result = process_modality_for_case(case_id, "audio")
    assert result is not None
    audio_mod = next(m for m in result.modalities if m.modality == "audio")
    assert audio_mod.status == "done"
    assert audio_mod.provider == "local"
    assert result.status == "done"
    assert result.risk_level is not None
    assert result.risk_score is not None


def test_process_audio_with_cb_open_uses_local_without_azure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_azure(_payload: bytes) -> dict[str, object]:
        calls.append("azure")
        raise AssertionError("Azure não deveria ser chamado")

    monkeypatch.setenv("AZURE_ENABLED", "true")
    monkeypatch.setenv("LIMEN_AZURE_CB_FORCE_OPEN", "true")
    monkeypatch.setattr(
        "app.azure.provider.default_azure_analyze",
        fake_azure,
    )

    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_audio_case(case_store=case_store, blob_store=blob_store)
    runtime_mod.configure_case_runtime(case_store, blob_store)

    result = process_modality_for_case(case_id, "audio")
    assert result is not None
    audio_mod = next(m for m in result.modalities if m.modality == "audio")
    assert audio_mod.status == "done"
    assert audio_mod.provider == "local"
    assert calls == []
