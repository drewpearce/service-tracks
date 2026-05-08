from unittest.mock import patch

from httpx import AsyncClient


async def test_health_endpoint(client: AsyncClient):
    """Health endpoint returns scheduler status; mock to isolate from scheduler state."""
    with patch(
        "app.routers.health.get_scheduler_status",
        return_value={"scheduler": "running", "scheduler_jobs": 0},
    ):
        response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["db"] == "ok"
    assert body["scheduler"] == "running"
