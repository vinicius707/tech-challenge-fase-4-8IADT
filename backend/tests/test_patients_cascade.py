from __future__ import annotations

import uuid

import pytest
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
from app.cases.service import CaseRecord, InMemoryCaseStore
from app.main import app
from app.patients.service import InMemoryPatientStore, PatientService, get_patient_service


@pytest.fixture
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-32b")
    monkeypatch.setenv("JWT_ACCESS_TTL_SECONDS", "900")


@pytest.fixture
def operator_store() -> InMemoryOperatorStore:
    return InMemoryOperatorStore()


@pytest.fixture
def patient_store() -> InMemoryPatientStore:
    return InMemoryPatientStore()


@pytest.fixture
def case_store() -> InMemoryCaseStore:
    return InMemoryCaseStore()


@pytest.fixture
def blacklist_store() -> InMemoryBlacklistStore:
    return InMemoryBlacklistStore()


@pytest.fixture
def client(
    auth_env: None,
    operator_store: InMemoryOperatorStore,
    patient_store: InMemoryPatientStore,
    case_store: InMemoryCaseStore,
    blacklist_store: InMemoryBlacklistStore,
) -> TestClient:
    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
    patient_service = PatientService(store=patient_store, case_store=case_store)
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_blacklist_store] = lambda: blacklist_store
    app.dependency_overrides[get_patient_service] = lambda: patient_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _seed_medico(store: InMemoryOperatorStore) -> OperatorRecord:
    operator = OperatorRecord(
        id=uuid.uuid4(),
        username="medico",
        password_hash=hash_password("medico-secret"),
        role="medico",
    )
    store.save(operator)
    return operator


def _auth_header(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": "medico", "password": "medico-secret"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_delete_patient_cascades_cases(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    case_store: InMemoryCaseStore,
) -> None:
    from datetime import UTC, datetime

    _seed_medico(operator_store)
    headers = _auth_header(client)
    created = client.post("/patients", headers=headers, json={}).json()
    patient_id = uuid.UUID(created["id"])
    now = datetime.now(tz=UTC)

    for _ in range(2):
        case_store.save(
            CaseRecord(
                id=uuid.uuid4(),
                patient_id=patient_id,
                status="pending",
                risk_score=None,
                risk_level=None,
                idempotency_key=str(uuid.uuid4()),
                content_sha256="abc",
                created_at=now,
                updated_at=now,
            )
        )
    assert sum(1 for c in case_store._by_id.values() if c.patient_id == patient_id) == 2

    deleted = client.delete(f"/patients/{patient_id}", headers=headers)

    assert deleted.status_code == 204
    assert sum(1 for c in case_store._by_id.values() if c.patient_id == patient_id) == 0


def test_cases_schema_declares_patient_fk_cascade() -> None:
    from sqlalchemy import inspect

    import app.patients.models  # noqa: F401 — registra tabela patients no MetaData
    from app.cases.models import Case

    foreign_keys = inspect(Case).mapper.columns["patient_id"].foreign_keys
    assert len(foreign_keys) == 1
    fk = next(iter(foreign_keys))
    assert fk.column.table.name == "patients"
    assert fk.ondelete == "CASCADE"
