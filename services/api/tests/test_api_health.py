from fastapi.testclient import TestClient

from arcturus_api.main import create_app


class TestHealthEndpoints:
    def test_liveness(self) -> None:
        with TestClient(create_app()) as client:
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_readiness_reports_database_state(self) -> None:
        # Passes with or without a live database: 200/ready when Postgres is
        # reachable, 503/degraded otherwise — both are valid probe responses.
        with TestClient(create_app()) as client:
            response = client.get("/health/ready")
        body = response.json()
        assert (response.status_code, body["status"]) in (
            (200, "ready"),
            (503, "degraded"),
        )
        assert body["database"] in ("up", "down")
