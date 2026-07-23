"""TDD T7.1 — Justificativa template determinística no GET do Caso."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.cases import runtime as runtime_mod
from app.cases.justification import build_justification
from app.cases.service import (
    ArtifactRecord,
    CaseRecord,
    CaseService,
    InMemoryCaseStore,
    ModalityRecord,
)
from app.cases.storage import InMemoryArtifactBlobStore
from app.cases.vitals_engine import ModalityRisk, VitalsAnomaly
from app.outbox import completion as completion_mod
from app.outbox.jobs import process_modality
from app.outbox.service import InMemoryOutboxStore, OutboxDispatcher, RecordingJobEnqueuer
from app.patients.service import InMemoryPatientStore

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_DIR = REPO_ROOT / "data" / "fixtures" / "vitals"


@pytest.fixture(autouse=True)
def reset_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    monkeypatch.delenv("LIMEN_FORCE_FAIL_MODALITIES", raising=False)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def test_build_justification_lists_done_weights_and_failed_unavailable() -> None:
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    modalities = [
        ModalityRecord(
            id=uuid.uuid4(),
            case_id=case_id,
            modality="vitals",
            status="done",
            artifact_id=uuid.uuid4(),
            created_at=now,
            updated_at=now,
        ),
        ModalityRecord(
            id=uuid.uuid4(),
            case_id=case_id,
            modality="audio",
            status="failed",
            artifact_id=None,
            created_at=now,
            updated_at=now,
        ),
    ]
    risks = {
        "vitals": ModalityRisk(
            score=0.55,
            level="MEDIO",
            anomalies=(
                VitalsAnomaly(metric="heart_rate", value=110.0, detail="FC elevada"),
                VitalsAnomaly(metric="spo2", value=92.0, detail="SpO2 baixa"),
            ),
        )
    }

    result = build_justification(
        modalities=modalities,
        risks_by_modality=risks,
        fused_score=0.55,
        fused_level="MEDIO",
    )

    assert result["narrative"]
    by_mod = {m["modality"]: m for m in result["modalities"]}
    assert by_mod["vitals"]["status"] == "done"
    assert by_mod["vitals"]["weight"] == pytest.approx(1.0)
    assert by_mod["vitals"]["partial_score"] == pytest.approx(0.55)
    assert by_mod["vitals"]["partial_level"] == "MEDIO"
    assert by_mod["vitals"]["top_anomalies"] == ["heart_rate", "spo2"]
    assert by_mod["audio"]["status"] == "failed"
    assert by_mod["audio"]["weight"] is None
    assert by_mod["audio"]["partial_score"] is None
    assert by_mod["audio"]["partial_level"] is None
    assert by_mod["audio"]["top_anomalies"] == []
    assert "indispon" in result["narrative"].lower() or "failed" in result["narrative"].lower()


def test_build_justification_is_deterministic() -> None:
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    modalities = [
        ModalityRecord(
            id=uuid.uuid4(),
            case_id=case_id,
            modality="vitals",
            status="done",
            artifact_id=uuid.uuid4(),
            created_at=now,
            updated_at=now,
        ),
        ModalityRecord(
            id=uuid.uuid4(),
            case_id=case_id,
            modality="audio",
            status="done",
            artifact_id=uuid.uuid4(),
            created_at=now,
            updated_at=now,
        ),
    ]
    risks = {
        "vitals": ModalityRisk(score=0.55, level="MEDIO", anomalies=()),
        "audio": ModalityRisk(score=0.85, level="ALTO", anomalies=()),
    }
    kwargs = dict(
        modalities=modalities,
        risks_by_modality=risks,
        fused_score=0.70,
        fused_level="ALTO",
    )
    assert build_justification(**kwargs) == build_justification(**kwargs)
    assert build_justification(**kwargs)["modalities"][0]["weight"] == pytest.approx(0.5)


def _seed_case_vitals_and_audio(
    *,
    case_store: InMemoryCaseStore,
    blob_store: InMemoryArtifactBlobStore,
    fixture_name: str = "vitals_medium.csv",
) -> uuid.UUID:
    content = (VITALS_DIR / fixture_name).read_bytes()
    now = datetime.now(tz=UTC)
    case_id = uuid.uuid4()
    vitals_artifact_id = uuid.uuid4()
    object_key = f"cases/{case_id}/vitals/{fixture_name}"
    blob_store.put(
        bucket="limen",
        object_key=object_key,
        content=content,
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
                    artifact_id=vitals_artifact_id,
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
                    id=vitals_artifact_id,
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


def test_get_case_includes_justification_after_partial_fusion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIMEN_FORCE_FAIL_MODALITIES", "audio")
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    case_id = _seed_case_vitals_and_audio(
        case_store=case_store, blob_store=blob_store
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)
    completion_mod.configure_completion_store(case_store)

    process_modality(str(case_id), "vitals")
    process_modality(str(case_id), "audio")

    service = CaseService(
        store=case_store,
        patient_store=InMemoryPatientStore(),
        blob_store=blob_store,
        outbox_dispatcher=OutboxDispatcher(
            store=InMemoryOutboxStore(),
            enqueuer=RecordingJobEnqueuer(),
        ),
    )
    response = service.get(case_id)
    assert response.status == "done"
    assert response.justification is not None
    assert response.justification.narrative
    first = response.justification.model_dump()
    second = service.get(case_id).justification.model_dump()
    assert first == second

    by_mod = {m.modality: m for m in response.justification.modalities}
    assert by_mod["vitals"].status == "done"
    assert by_mod["vitals"].weight == pytest.approx(1.0)
    assert by_mod["vitals"].partial_level == "MEDIO"
    assert by_mod["audio"].status == "failed"
    assert by_mod["audio"].weight is None
