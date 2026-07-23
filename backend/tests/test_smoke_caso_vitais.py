"""TDD T8.1 — smoke Caso vitais (contrato HTTP: health → login → paciente → caso → done)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
from app.cases import runtime as runtime_mod
from app.cases.service import CaseService, InMemoryCaseStore, get_case_service
from app.cases.storage import InMemoryArtifactBlobStore
from app.health import HealthService, get_health_service
from app.main import app
from app.outbox import completion as completion_mod
from app.outbox.jobs import process_modality
from app.outbox.service import (
    InMemoryOutboxStore,
    OutboxDispatcher,
    RecordingJobEnqueuer,
)
from app.patients.service import InMemoryPatientStore, PatientService, get_patient_service
from app.smoke.caso_vitais import (
    SmokeCasoVitaisConfig,
    SmokeCasoVitaisError,
    SmokeCasoVitaisResult,
    run_smoke_caso_vitais,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
VITALS_MEDIUM = REPO_ROOT / "data" / "fixtures" / "vitals" / "vitals_medium.csv"
SCRIPT_SH = REPO_ROOT / "scripts" / "smoke-caso-vitais.sh"
SCRIPT_PY = REPO_ROOT / "scripts" / "smoke_caso_vitais.py"


@dataclass
class _FakeResponse:
    status_code: int
    body: Any
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class _FakeTransport:
    """Transport in-memory: roteia por método+path."""

    responses: dict[tuple[str, str], list[_FakeResponse]]
    calls: list[tuple[str, str]] = field(default_factory=list)
    multipart_calls: list[str] = field(default_factory=list)

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        multipart_file: tuple[str, bytes, str] | None = None,
    ) -> tuple[int, Any]:
        del headers, json_body
        method_u = method.upper()
        if multipart_file is not None:
            self.multipart_calls.append(path)
        self.calls.append((method_u, path))

        key = (method_u, path)
        if key not in self.responses and method_u == "GET" and path.startswith(
            "/cases/"
        ):
            key = ("GET", "/cases/{id}")
        if key not in self.responses and method_u == "POST" and path.endswith(
            "/cases"
        ):
            for stored in self.responses:
                if stored[0] == "POST" and stored[1].endswith("/cases"):
                    key = stored
                    break

        queue = self.responses.get(key)
        if not queue:
            raise AssertionError(f"Sem resposta fake para {method_u} {path}")
        resp = queue.pop(0) if len(queue) > 1 else queue[0]
        return resp.status_code, resp.body


@pytest.fixture(autouse=True)
def reset_runtime() -> None:
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)
    yield
    runtime_mod.configure_case_runtime(None, None)
    completion_mod.configure_completion_store(None)


def test_script_files_exist_and_document_azure_false() -> None:
    assert SCRIPT_SH.is_file()
    assert SCRIPT_PY.is_file()
    sh_text = SCRIPT_SH.read_text(encoding="utf-8")
    py_text = SCRIPT_PY.read_text(encoding="utf-8")
    assert "AZURE_ENABLED" in sh_text or "AZURE_ENABLED" in py_text
    assert "smoke-caso-vitais" in sh_text or "smoke_caso_vitais" in sh_text


def test_fake_transport_reaches_done_without_video_audio_rx() -> None:
    case_id = str(uuid.uuid4())
    patient_id = str(uuid.uuid4())
    transport = _FakeTransport(
        responses={
            ("GET", "/health"): [
                _FakeResponse(
                    200,
                    {
                        "status": "ok",
                        "checks": {
                            "postgres": "ok",
                            "redis": "ok",
                            "minio": "ok",
                        },
                    },
                )
            ],
            ("POST", "/auth/login"): [
                _FakeResponse(200, {"access_token": "tok", "token_type": "bearer"})
            ],
            ("POST", "/patients"): [
                _FakeResponse(201, {"id": patient_id, "code": "PAC-001"})
            ],
            ("POST", f"/patients/{patient_id}/cases"): [
                _FakeResponse(201, {"id": case_id, "status": "pending"})
            ],
            ("GET", "/cases/{id}"): [
                _FakeResponse(200, {"id": case_id, "status": "processing"}),
                _FakeResponse(
                    200,
                    {
                        "id": case_id,
                        "status": "done",
                        "modalities": [{"modality": "vitals", "status": "done"}],
                    },
                ),
            ],
        }
    )
    result = run_smoke_caso_vitais(
        SmokeCasoVitaisConfig(
            base_url="http://test",
            username="medico",
            password="x",
            vitals_csv_path=VITALS_MEDIUM,
            poll_timeout_seconds=5,
            poll_interval_seconds=0,
        ),
        transport=transport,
        sleep=lambda _s: None,
    )

    assert isinstance(result, SmokeCasoVitaisResult)
    assert result.case_id == case_id
    assert result.status == "done"
    assert transport.multipart_calls
    assert all(
        "video" not in p and "audio" not in p and "prescriptions" not in p
        for p in transport.multipart_calls
    )
    assert all(
        "modalities/video" not in c[1]
        and "modalities/audio" not in c[1]
        and "modalities/prescriptions" not in c[1]
        for c in transport.calls
    )


def test_timeout_includes_case_id_and_last_status() -> None:
    case_id = str(uuid.uuid4())
    patient_id = str(uuid.uuid4())
    transport = _FakeTransport(
        responses={
            ("GET", "/health"): [
                _FakeResponse(
                    200,
                    {
                        "status": "ok",
                        "checks": {
                            "postgres": "ok",
                            "redis": "ok",
                            "minio": "ok",
                        },
                    },
                )
            ],
            ("POST", "/auth/login"): [
                _FakeResponse(200, {"access_token": "tok", "token_type": "bearer"})
            ],
            ("POST", "/patients"): [
                _FakeResponse(201, {"id": patient_id, "code": "PAC-001"})
            ],
            ("POST", f"/patients/{patient_id}/cases"): [
                _FakeResponse(201, {"id": case_id, "status": "pending"})
            ],
            ("GET", "/cases/{id}"): [
                _FakeResponse(200, {"id": case_id, "status": "processing"}),
            ],
        }
    )
    ticks = {"n": 0}

    def clock() -> float:
        # 0: deadline base; 1+: já estourou o timeout curto
        ticks["n"] += 1
        return 0.0 if ticks["n"] == 1 else 1.0

    with pytest.raises(SmokeCasoVitaisError) as excinfo:
        run_smoke_caso_vitais(
            SmokeCasoVitaisConfig(
                base_url="http://test",
                username="medico",
                password="x",
                vitals_csv_path=VITALS_MEDIUM,
                poll_timeout_seconds=0.01,
                poll_interval_seconds=0,
            ),
            transport=transport,
            sleep=lambda _s: None,
            clock=clock,
        )

    message = str(excinfo.value)
    assert case_id in message
    assert "processing" in message


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.setenv("JWT_ACCESS_TTL_SECONDS", "900")
    monkeypatch.setenv("PII_ENCRYPTION_KEY", Fernet.generate_key().decode())


@pytest.fixture
def wired_client(
    auth_env: None,
) -> tuple[TestClient, RecordingJobEnqueuer, InMemoryCaseStore, InMemoryArtifactBlobStore, InMemoryOutboxStore]:
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
    outbox_store = InMemoryOutboxStore()
    enqueuer = RecordingJobEnqueuer()
    blacklist_store = InMemoryBlacklistStore()
    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
    patient_service = PatientService(store=patient_store, case_store=case_store)
    case_service = CaseService(
        store=case_store,
        patient_store=patient_store,
        blob_store=blob_store,
        outbox_dispatcher=OutboxDispatcher(store=outbox_store, enqueuer=enqueuer),
    )
    runtime_mod.configure_case_runtime(case_store, blob_store)
    completion_mod.configure_completion_store(outbox_store)

    health = HealthService(
        {"postgres": lambda: True, "redis": lambda: True, "minio": lambda: True}
    )
    app.dependency_overrides[get_health_service] = lambda: health
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_blacklist_store] = lambda: blacklist_store
    app.dependency_overrides[get_patient_service] = lambda: patient_service
    app.dependency_overrides[get_case_service] = lambda: case_service
    with TestClient(app) as test_client:
        yield test_client, enqueuer, case_store, blob_store, outbox_store
    app.dependency_overrides.clear()


class _TestClientTransport:
    """Adapta TestClient ao contrato do smoke; drena jobs RQ fake no poll."""

    def __init__(
        self,
        client: TestClient,
        enqueuer: RecordingJobEnqueuer,
        outbox_store: InMemoryOutboxStore,
    ) -> None:
        self._client = client
        self._enqueuer = enqueuer
        self._outbox_store = outbox_store
        self._drained: set[str] = set()

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        multipart_file: tuple[str, bytes, str] | None = None,
    ) -> tuple[int, Any]:
        headers = headers or {}
        if method.upper() == "GET":
            if path.startswith("/cases/"):
                self._drain_pending_jobs()
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
            raise AssertionError(f"método não suportado: {method}")
        body: Any
        try:
            body = response.json()
        except Exception:
            body = response.text
        return response.status_code, body

    def _drain_pending_jobs(self) -> None:
        for job in list(self._enqueuer.jobs):
            rq_id = job["rq_job_id"]
            if rq_id in self._drained:
                continue
            payload = job["payload"]
            case_id = payload["case_id"]
            modality = payload["modality"]
            # Resolve outbox job id from store by aggregate
            outbox_job_id = None
            for record in self._outbox_store.list_by_statuses(
                ("enqueued", "pending", "enqueue_failed")
            ):
                if str(record.aggregate_id) == case_id and record.payload.get(
                    "modality"
                ) == modality:
                    outbox_job_id = str(record.id)
                    break
            process_modality(
                case_id,
                modality,
                outbox_job_id=outbox_job_id,
            )
            self._drained.add(rq_id)


def test_smoke_against_testclient_reaches_done(
    wired_client: tuple[
        TestClient,
        RecordingJobEnqueuer,
        InMemoryCaseStore,
        InMemoryArtifactBlobStore,
        InMemoryOutboxStore,
    ],
) -> None:
    client, enqueuer, _case_store, _blob, outbox_store = wired_client
    transport = _TestClientTransport(client, enqueuer, outbox_store)

    result = run_smoke_caso_vitais(
        SmokeCasoVitaisConfig(
            base_url="http://test",
            username="medico",
            password="medico_dev_only",
            vitals_csv_path=VITALS_MEDIUM,
            idempotency_key=f"smoke-test-{uuid.uuid4()}",
            poll_timeout_seconds=5,
            poll_interval_seconds=0,
        ),
        transport=transport,
        sleep=lambda _s: None,
    )

    assert result.status == "done"
    assert result.case_id
    detail = client.get(
        f"/cases/{result.case_id}",
        headers={
            "Authorization": (
                "Bearer "
                + client.post(
                    "/auth/login",
                    json={"username": "medico", "password": "medico_dev_only"},
                ).json()["access_token"]
            )
        },
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "done"
    modalities = {m["modality"]: m["status"] for m in body["modalities"]}
    assert modalities.get("vitals") == "done"
    assert "video" not in modalities
    assert "audio" not in modalities
    assert "prescriptions" not in modalities
