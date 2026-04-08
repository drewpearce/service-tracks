from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    """Health endpoint returns scheduler status; mock to isolate from scheduler state."""
    client = TestClient(app)
    with patch(
        "app.routers.health.get_scheduler_status",
        return_value={"scheduler": "running", "scheduler_jobs": 0},
    ):
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["db"] == "ok"
    assert body["scheduler"] == "running"
