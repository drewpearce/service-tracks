from httpx import AsyncClient


async def test_security_headers_present_on_normal_response(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


async def test_hsts_absent_outside_production(client: AsyncClient):
    response = await client.get("/api/health")
    assert "Strict-Transport-Security" not in response.headers


async def test_hsts_present_in_production(client: AsyncClient, monkeypatch):
    monkeypatch.setattr("app.middleware.security_headers.settings.ENVIRONMENT", "production")

    response = await client.get("/api/health")
    assert response.headers["Strict-Transport-Security"] == "max-age=63072000; includeSubDomains"


async def test_csp_absent_on_exempt_docs_path(client: AsyncClient):
    response = await client.get("/openapi.json")
    assert "Content-Security-Policy" not in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
