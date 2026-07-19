from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_all_dependencies_as_ready() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "postgres": "ok",
            "redis": "ok",
            "minio": "ok",
        },
    }
