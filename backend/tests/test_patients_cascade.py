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
from app.main import app
from app.patients.cases_stub import InMemoryCaseStubStore
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
def case_stub_store() -> InMemoryCaseStubStore:
    return InMemoryCaseStubStore()


@pytest.fixture
def blacklist_store() -> InMemoryBlacklistStore:
    return InMemoryBlacklistStore()


@pytest.fixture
def client(
    auth_env: None,
    operator_store: InMemoryOperatorStore,
    patient_store: InMemoryPatientStore,
    case_stub_store: InMemoryCaseStubStore,
    blacklist_store: InMemoryBlacklistStore,
) -> TestClient:
    auth_service = AuthService(store=operator_store, blacklist_store=blacklist_store)
    patient_service = PatientService(
        store=patient_store,
        case_stub_store=case_stub_store,
    )
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


def test_delete_patient_cascades_stub_cases(
    client: TestClient,
    operator_store: InMemoryOperatorStore,
    case_stub_store: InMemoryCaseStubStore,
) -> None:
    _seed_medico(operator_store)
    headers = _auth_header(client)
    created = client.post("/patients", headers=headers, json={}).json()
    patient_id = uuid.UUID(created["id"])

    case_stub_store.save_for_patient(patient_id)
    case_stub_store.save_for_patient(patient_id)
    assert len(case_stub_store.list_by_patient(patient_id)) == 2

    deleted = client.delete(f"/patients/{patient_id}", headers=headers)

    assert deleted.status_code == 204
    assert case_stub_store.list_by_patient(patient_id) == []


def test_cases_stub_schema_declares_patient_fk_cascade() -> None:
    from sqlalchemy import inspect

    from app.patients.models import CaseStub

    foreign_keys = inspect(CaseStub).mapper.columns["patient_id"].foreign_keys
    assert len(foreign_keys) == 1
    fk = next(iter(foreign_keys))
    assert fk.column.table.name == "patients"
    assert fk.ondelete == "CASCADE"
