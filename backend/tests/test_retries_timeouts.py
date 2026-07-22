"""TDD T5.6 — retries classificados + timeouts por modalidade."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

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
from app.outbox.retries import (
    PermanentProcessingError,
    RetryPolicy,
    TransientProcessingError,
    classify_error,
)
from app.outbox.timeouts import modality_timeout_seconds

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_NORMAL = (
    REPO_ROOT / "data" / "fixtures" / "vitals" / "vitals_normal.csv"
).read_bytes()


@pytest.fixture(autouse=True)
def reset_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    for key in (
        "LIMEN_FORCE_FAIL_MODALITIES",
        "LIMEN_FORCE_SLOW_MODALITIES",
        "LIMEN_FORCE_SLOW_SECONDS",
        "LIMEN_FORCE_PERMANENT_FAIL_MODALITIES",
        "LIMEN_FORCE_TRANSIENT_FAIL_MODALITIES",
        "LIMEN_TIMEOUT_AUDIO_SECONDS",
        "LIMEN_TIMEOUT_VITALS_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def test_classify_transient_and_permanent_errors() -> None:
    assert classify_error(TransientProcessingError("429")) == "transient"
    assert classify_error(TimeoutError("network")) == "transient"
    assert classify_error(ConnectionError("down")) == "transient"
    assert classify_error(PermanentProcessingError("invalid")) == "permanent"
    assert classify_error(ValueError("bad csv")) == "permanent"


def test_retry_policy_retries_transient_until_max() -> None:
    policy = RetryPolicy(max_attempts=3, base_delay_seconds=1.0)
    err = TransientProcessingError("busy")

    assert policy.should_retry(err, attempt=1) is True
    assert policy.should_retry(err, attempt=2) is True
    assert policy.should_retry(err, attempt=3) is False
    assert policy.backoff_seconds(1) == 1.0
    assert policy.backoff_seconds(2) == 2.0
    assert policy.backoff_seconds(3) == 4.0


def test_retry_policy_does_not_retry_permanent() -> None:
    policy = RetryPolicy(max_attempts=5)
    assert policy.should_retry(PermanentProcessingError("bad"), attempt=1) is False


def test_modality_timeout_defaults_and_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LIMEN_TIMEOUT_VITALS_SECONDS", raising=False)
    monkeypatch.delenv("LIMEN_TIMEOUT_AUDIO_SECONDS", raising=False)
    monkeypatch.delenv("LIMEN_TIMEOUT_VIDEO_SECONDS", raising=False)

    assert modality_timeout_seconds("vitals") == 30
    assert modality_timeout_seconds("audio") == 90
    assert modality_timeout_seconds("video") == 180

    monkeypatch.setenv("LIMEN_TIMEOUT_AUDIO_SECONDS", "0.05")
    assert modality_timeout_seconds("audio") == pytest.approx(0.05)


def _seed_vitals_and_audio(
    *,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
) -> uuid.UUID:
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    object_key = f"cases/{case_id}/vitals/vitals_normal.csv"
    blob_store.put(
        bucket="limen",
        object_key=object_key,
        content=VITALS_NORMAL,
        content_type="text/csv",
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
                    modality="vitals",
                    status="pending",
                    artifact_id=artifact_id,
                    created_at=now,
                    updated_at=now,
                ),
                ModalityRecord(
                    id=uuid.uuid4(),
                    case_id=case_id,
                    modality="audio",
                    status="pending",
                    artifact_id=None,
                    created_at=now,
                    updated_at=now,
                ),
            ],
            artifacts=[
                ArtifactRecord(
                    id=artifact_id,
                    case_id=case_id,
                    modality="vitals",
                    bucket="limen",
                    object_key=object_key,
                    content_sha256="x",
                    content_type="text/csv",
                    created_at=now,
                )
            ],
        )
    )
    return case_id


def test_modality_timeout_marks_failed_and_others_can_finish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cenário 3: timeout → modalidade failed; demais seguem (falha parcial)."""
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_vitals_and_audio(case_store=case_store, blob_store=blob_store)
    runtime_mod.configure_case_runtime(case_store, blob_store)

    monkeypatch.setenv("LIMEN_TIMEOUT_AUDIO_SECONDS", "0.05")
    monkeypatch.setenv("LIMEN_FORCE_SLOW_MODALITIES", "audio")
    monkeypatch.setenv("LIMEN_FORCE_SLOW_SECONDS", "1")

    process_modality_for_case(case_id, "audio")
    mid = case_store.get(case_id)
    assert mid is not None
    assert next(m.status for m in mid.modalities if m.modality == "audio") == "failed"
    assert next(m.status for m in mid.modalities if m.modality == "vitals") == "pending"
    assert mid.status == "processing"

    process_modality_for_case(case_id, "vitals")
    done = case_store.get(case_id)
    assert done is not None
    assert {m.modality: m.status for m in done.modalities} == {
        "vitals": "done",
        "audio": "failed",
    }
    assert done.status == "done"
    assert done.risk_level == "BAIXO"


def test_permanent_error_marks_modality_failed_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_vitals_and_audio(case_store=case_store, blob_store=blob_store)
    runtime_mod.configure_case_runtime(case_store, blob_store)
    monkeypatch.setenv("LIMEN_FORCE_PERMANENT_FAIL_MODALITIES", "audio")

    result = process_modality_for_case(case_id, "audio")
    assert result is not None
    assert next(m.status for m in result.modalities if m.modality == "audio") == "failed"


def test_transient_error_propagates_for_rq_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_vitals_and_audio(case_store=case_store, blob_store=blob_store)
    runtime_mod.configure_case_runtime(case_store, blob_store)
    monkeypatch.setenv("LIMEN_FORCE_TRANSIENT_FAIL_MODALITIES", "audio")

    with pytest.raises(TransientProcessingError):
        process_modality_for_case(case_id, "audio")

    case = case_store.get(case_id)
    assert case is not None
    # Não fecha como failed permanente — fica processing para retry.
    assert next(m.status for m in case.modalities if m.modality == "audio") == "processing"


def test_enqueue_passes_job_timeout_for_modality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.outbox.rq_client import enqueue_process_modality

    captured: dict[str, object] = {}

    class _FakeQueue:
        def enqueue(self, *args, **kwargs):  # noqa: ANN002, ANN003
            captured["kwargs"] = kwargs

            class _Job:
                id = "rq-1"

            return _Job()

    monkeypatch.setattr(
        "app.outbox.rq_client.get_queue",
        lambda *a, **k: _FakeQueue(),
    )
    monkeypatch.setenv("LIMEN_TIMEOUT_VITALS_SECONDS", "12")

    enqueue_process_modality(case_id=str(uuid.uuid4()), modality="vitals")

    assert captured["kwargs"]["job_timeout"] == 12
