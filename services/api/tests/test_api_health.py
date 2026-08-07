from fastapi.testclient import TestClient

from arcturus_api.main import create_app


class TestHealthEndpoints:
    def test_liveness(self) -> None:
        with TestClient(create_app()) as client:
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_readiness(self) -> None:
        with TestClient(create_app()) as client:
            response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
