"""TDD T8.5 — seed multimodal via HTTP (Compose / API real)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.auth.passwords import hash_password
from app.auth.service import (
    AuthService,
    InMemoryBlacklistStore,
    InMemoryOperatorStore,
    OperatorRecord,
    get_auth_service,
    get_blacklist_store,
)
from app.cases.multimodal_seed import (
    DEMO_AUDIO_IDEMPOTENCY_KEY,
    DEMO_CASE_IDEMPOTENCY_KEY,
    DEMO_PRESCRIPTIONS_IDEMPOTENCY_KEY,
    DEMO_VIDEO_IDEMPOTENCY_KEY,
)
from app.cases.multimodal_seed_http import (
    MultimodalSeedHttpConfig,
    MultimodalSeedHttpError,
    seed_multimodal_demo_http,
)
from app.cases.service import CaseService, InMemoryCaseStore, get_case_service
from app.cases.storage import InMemoryArtifactBlobStore
from app.main import app
from app.outbox.service import InMemoryOutboxStore, OutboxDispatcher, RecordingJobEnqueuer
from app.patients.service import InMemoryPatientStore, PatientService, get_patient_service
from app.smoke.caso_vitais import SmokeTransport

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_SH = REPO_ROOT / "scripts" / "seed-multimodal-demo.sh"
SCRIPT_PY = REPO_ROOT / "scripts" / "seed_multimodal_demo.py"


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.setenv("JWT_ACCESS_TTL_SECONDS", "900")
    monkeypatch.setenv("PII_ENCRYPTION_KEY", Fernet.generate_key().decode())


@pytest.fixture
def wired_client(auth_env: None) -> TestClient:
    operator_store = InMemoryOperatorStore()
    operator_store.save(
        OperatorRecord(
            id=uuid.uuid4(),
            username="medico",
            password_hash=hash_password("medico_dev_only"),
            role="medico",
        )
    )
    patient_store = InMemoryPatientStore()
    case_store = InMemoryCaseStore()
    blob_store = InMemoryArtifactBlobStore()
    blacklist_store = InMemoryBlacklistStore()
    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
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
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_blacklist_store] = lambda: blacklist_store
    app.dependency_overrides[get_patient_service] = lambda: patient_service
    app.dependency_overrides[get_case_service] = lambda: case_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


class _TestClientTransport:
    def __init__(self, client: TestClient) -> None:
        self._client = client

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict | None = None,
        multipart_file: tuple[str, bytes, str] | None = None,
    ) -> tuple[int, object]:
        headers = headers or {}
        if method.upper() == "GET":
            response = self._client.get(path, headers=headers)
        elif method.upper() == "POST" and multipart_file is not None:
            filename, content, content_type = multipart_file
            response = self._client.post(
                path,
                headers=headers,
                files={"file": (filename, content, content_type)},
            )
        elif method.upper() == "POST":
            response = self._client.post(path, headers=headers, json=json_body or {})
        else:
            raise AssertionError(method)
        try:
            body: object = response.json()
        except Exception:
            body = response.text
        return response.status_code, body


def test_seed_scripts_exist_and_document_http_compose() -> None:
    assert SCRIPT_SH.is_file()
    assert SCRIPT_PY.is_file()
    sh = SCRIPT_SH.read_text(encoding="utf-8")
    py = SCRIPT_PY.read_text(encoding="utf-8")
    assert "--http" in py or "seed_multimodal_demo_http" in py
    assert "AZURE_ENABLED" in sh or "Compose" in sh or "LIMEN_API" in sh


def test_http_seed_creates_four_modalities(wired_client: TestClient) -> None:
    transport: SmokeTransport = _TestClientTransport(wired_client)
    result = seed_multimodal_demo_http(
        MultimodalSeedHttpConfig(
            base_url="http://test",
            username="medico",
            password="medico_dev_only",
        ),
        transport=transport,
    )
    assert result.case_id
    assert result.patient_id
    assert set(result.modalities) == {"vitals", "video", "audio", "prescriptions"}
    assert result.created_case is True


def test_http_seed_is_idempotent_on_replay(wired_client: TestClient) -> None:
    transport = _TestClientTransport(wired_client)
    config = MultimodalSeedHttpConfig(
        base_url="http://test",
        username="medico",
        password="medico_dev_only",
    )
    first = seed_multimodal_demo_http(config, transport=transport)
    second = seed_multimodal_demo_http(config, transport=transport)
    assert first.case_id == second.case_id
    assert second.created_case is False
    assert set(second.modalities) == {"vitals", "video", "audio", "prescriptions"}


def test_http_seed_uses_documented_demo_keys() -> None:
    assert DEMO_CASE_IDEMPOTENCY_KEY.startswith("limen-demo-multimodal-")
    assert DEMO_VIDEO_IDEMPOTENCY_KEY.startswith("limen-demo-multimodal-")
    assert DEMO_AUDIO_IDEMPOTENCY_KEY.startswith("limen-demo-multimodal-")
    assert DEMO_PRESCRIPTIONS_IDEMPOTENCY_KEY.startswith("limen-demo-multimodal-")


def test_http_seed_fails_without_auth(wired_client: TestClient) -> None:
    transport = _TestClientTransport(wired_client)
    with pytest.raises(MultimodalSeedHttpError):
        seed_multimodal_demo_http(
            MultimodalSeedHttpConfig(
                base_url="http://test",
                username="medico",
                password="wrong",
            ),
            transport=transport,
        )
