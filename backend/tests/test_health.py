from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.health import HealthService, get_health_service
from app.main import app

DEPENDENCIES = ("postgres", "redis", "minio")


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_health_reports_all_dependencies_as_ready() -> None:
    service = HealthService({name: lambda: True for name in DEPENDENCIES})
    app.dependency_overrides[get_health_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "postgres": "ok",
            "redis": "ok",
            "minio": "ok",
        },
    }


@pytest.mark.parametrize("unavailable_dependency", DEPENDENCIES)
def test_health_reports_an_unavailable_dependency(
    unavailable_dependency: str,
) -> None:
    checks: dict[str, Callable[[], bool]] = {
        name: (lambda result=name != unavailable_dependency: result)
        for name in DEPENDENCIES
    }
    app.dependency_overrides[get_health_service] = lambda: HealthService(checks)

    with TestClient(app) as client:
        response = client.get("/health")

    expected_checks = {name: "ok" for name in DEPENDENCIES}
    expected_checks[unavailable_dependency] = "error"

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "checks": expected_checks,
    }


def test_health_does_not_expose_dependency_error_details() -> None:
    sensitive_message = "postgresql://user:secret@internal-db/limen"

    def failing_check() -> bool:
        raise ConnectionError(sensitive_message)

    service = HealthService(
        {
            "postgres": failing_check,
            "redis": lambda: True,
            "minio": lambda: True,
        }
    )
    app.dependency_overrides[get_health_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["checks"]["postgres"] == "error"
    assert sensitive_message not in response.text
