"""PCO endpoint integration tests — Epic 4.

Tests use real PostgreSQL (service_tracks_test DB) with per-test transaction rollback.
Outbound PCO HTTP calls are mocked via respx.
asyncio_mode = "auto" (set in pyproject.toml) makes all async test functions run automatically.
"""

from datetime import datetime, timezone

import respx
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.church import Church
from app.models.church_user import ChurchUser
from app.models.pco_connection import PcoConnection
from app.utils.encryption import decrypt, encrypt
from tests.fixtures.pco_responses import (
    SINGLE_SERVICE_TYPE_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALID_SERVICE_TYPES_RESPONSE,
)

PCO_BASE = "https://api.planningcenteronline.com"


# ---------------------------------------------------------------------------
# POST /api/pco/connect
# ---------------------------------------------------------------------------


@respx.mock
async def test_pco_connect_success(verified_authenticated_client: AsyncClient, db: AsyncSession):
    respx.get(f"{PCO_BASE}/services/v2/service_types").mock(
        return_value=Response(200, json=VALID_SERVICE_TYPES_RESPONSE)
    )
    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    response = await verified_authenticated_client.post(
        "/api/pco/connect",
        json={"application_id": "my_app_id", "secret": "my_secret"},
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert len(body["service_types"]) == 2
    assert body["service_types"][0]["id"] == "111"
    assert body["service_types"][0]["name"] == "Sunday Morning"

    # Verify the pco_connection row was created in the DB
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = user_result.scalar_one()
    conn_result = await db.execute(select(PcoConnection).where(PcoConnection.church_id == user.church_id))
    conn = conn_result.scalar_one()
    assert conn.status == "active"
    assert conn.auth_method == "api_key"
    assert decrypt(conn.app_id_encrypted) == "my_app_id"
    assert decrypt(conn.secret_encrypted) == "my_secret"


@respx.mock
async def test_pco_connect_invalid_credentials(verified_authenticated_client: AsyncClient):
    respx.get(f"{PCO_BASE}/services/v2/service_types").mock(return_value=Response(401, json=UNAUTHORIZED_RESPONSE))
    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    response = await verified_authenticated_client.post(
        "/api/pco/connect",
        json={"application_id": "bad_id", "secret": "bad_secret"},
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_credentials"


async def test_pco_connect_unauthenticated(client: AsyncClient):
    """A POST without a session cookie should return 401 (auth) or 403 (CSRF).

    First do a GET to obtain a CSRF token cookie, then POST with that token but
    no session cookie — auth middleware returns 401.
    """
    # GET any endpoint to trigger CSRF cookie issuance
    await client.get("/api/health")
    csrf = client.cookies.get("csrf_token", "")
    response = await client.post(
        "/api/pco/connect",
        json={"application_id": "my_app_id", "secret": "my_secret"},
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 401


async def test_pco_connect_unverified_email(authenticated_client: AsyncClient):
    """User is registered but email is not verified — should get 403."""
    csrf = authenticated_client.cookies.get("csrf_token", "")
    response = await authenticated_client.post(
        "/api/pco/connect",
        json={"application_id": "my_app_id", "secret": "my_secret"},
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "email_not_verified"


@respx.mock
async def test_pco_connect_updates_existing(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """Connecting twice should update the existing row, not create a duplicate."""
    # First connect
    respx.get(f"{PCO_BASE}/services/v2/service_types").mock(
        return_value=Response(200, json=VALID_SERVICE_TYPES_RESPONSE)
    )
    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    r1 = await verified_authenticated_client.post(
        "/api/pco/connect",
        json={"application_id": "app_id_v1", "secret": "secret_v1"},
        headers={"x-csrf-token": csrf},
    )
    assert r1.status_code == 200

    # Second connect with different credentials
    respx.get(f"{PCO_BASE}/services/v2/service_types").mock(
        return_value=Response(200, json=VALID_SERVICE_TYPES_RESPONSE)
    )
    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    r2 = await verified_authenticated_client.post(
        "/api/pco/connect",
        json={"application_id": "app_id_v2", "secret": "secret_v2"},
        headers={"x-csrf-token": csrf},
    )
    assert r2.status_code == 200

    # Should be exactly one pco_connection row
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = user_result.scalar_one()
    conn_results = await db.execute(select(PcoConnection).where(PcoConnection.church_id == user.church_id))
    conns = conn_results.scalars().all()
    assert len(conns) == 1
    assert decrypt(conns[0].app_id_encrypted) == "app_id_v2"
    assert decrypt(conns[0].secret_encrypted) == "secret_v2"


# ---------------------------------------------------------------------------
# GET /api/pco/status
# ---------------------------------------------------------------------------


async def test_pco_status_connected(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """When a pco_connection exists, status should return connected=True."""
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = user_result.scalar_one()

    now = datetime.now(timezone.utc)
    conn = PcoConnection(
        church_id=user.church_id,
        auth_method="api_key",
        app_id_encrypted=encrypt("test_app_id"),
        secret_encrypted=encrypt("test_secret"),
        status="active",
        last_successful_call_at=now,
    )
    db.add(conn)
    await db.flush()

    response = await verified_authenticated_client.get("/api/pco/status")
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True
    assert body["auth_method"] == "api_key"
    assert body["status"] == "active"
    assert body["last_successful_call_at"] is not None


async def test_pco_status_not_connected(verified_authenticated_client: AsyncClient):
    """When no pco_connection exists, status should return connected=False."""
    response = await verified_authenticated_client.get("/api/pco/status")
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is False
    assert body["auth_method"] is None
    assert body["status"] is None
    assert body["last_successful_call_at"] is None


# ---------------------------------------------------------------------------
# POST /api/pco/select-service-type
# ---------------------------------------------------------------------------


@respx.mock
async def test_pco_select_service_type_success(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """Select a valid service type — church record should be updated."""
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = user_result.scalar_one()

    conn = PcoConnection(
        church_id=user.church_id,
        auth_method="api_key",
        app_id_encrypted=encrypt("test_app_id"),
        secret_encrypted=encrypt("test_secret"),
        status="active",
        last_successful_call_at=datetime.now(timezone.utc),
    )
    db.add(conn)
    await db.flush()

    respx.get(f"{PCO_BASE}/services/v2/service_types/111").mock(
        return_value=Response(200, json=SINGLE_SERVICE_TYPE_RESPONSE)
    )

    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    response = await verified_authenticated_client.post(
        "/api/pco/select-service-type",
        json={"service_type_id": "111"},
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["service_type_id"] == "111"
    assert body["service_type_name"] == "Sunday Morning"

    # Verify church record was updated
    church_result = await db.execute(select(Church).where(Church.id == user.church_id))
    church = church_result.scalar_one()
    assert church.pco_service_type_id == "111"
    assert church.sync_enabled is True


@respx.mock
async def test_pco_select_service_type_invalid(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """Selecting a service type that doesn't exist should return 400."""
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = user_result.scalar_one()

    conn = PcoConnection(
        church_id=user.church_id,
        auth_method="api_key",
        app_id_encrypted=encrypt("test_app_id"),
        secret_encrypted=encrypt("test_secret"),
        status="active",
        last_successful_call_at=datetime.now(timezone.utc),
    )
    db.add(conn)
    await db.flush()

    respx.get(f"{PCO_BASE}/services/v2/service_types/999").mock(
        return_value=Response(404, json={"errors": [{"status": "404", "title": "Not Found"}]})
    )

    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    response = await verified_authenticated_client.post(
        "/api/pco/select-service-type",
        json={"service_type_id": "999"},
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_service_type"


async def test_pco_select_service_type_no_connection(verified_authenticated_client: AsyncClient):
    """Selecting a service type without a PCO connection should return 400."""
    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    response = await verified_authenticated_client.post(
        "/api/pco/select-service-type",
        json={"service_type_id": "111"},
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "pco_not_connected"


# ---------------------------------------------------------------------------
# GET /api/pco/status — service_type_id and service_type_name fields
# ---------------------------------------------------------------------------


async def test_pco_status_no_service_type(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """When no service type is set, both fields are null."""
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = user_result.scalar_one()

    conn = PcoConnection(
        church_id=user.church_id,
        auth_method="api_key",
        app_id_encrypted=encrypt("test_app_id"),
        secret_encrypted=encrypt("test_secret"),
        status="active",
        last_successful_call_at=datetime.now(timezone.utc),
    )
    db.add(conn)
    await db.flush()

    response = await verified_authenticated_client.get("/api/pco/status")
    assert response.status_code == 200
    body = response.json()
    assert body["service_type_id"] is None
    assert body["service_type_name"] is None


@respx.mock
async def test_pco_status_with_service_type(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """When service type is set and PCO API succeeds, both fields are returned."""
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = user_result.scalar_one()

    conn = PcoConnection(
        church_id=user.church_id,
        auth_method="api_key",
        app_id_encrypted=encrypt("test_app_id"),
        secret_encrypted=encrypt("test_secret"),
        status="active",
        last_successful_call_at=datetime.now(timezone.utc),
    )
    db.add(conn)

    church_result = await db.execute(select(Church).where(Church.id == user.church_id))
    church = church_result.scalar_one()
    church.pco_service_type_id = "111"
    await db.flush()

    respx.get(f"{PCO_BASE}/services/v2/service_types/111").mock(
        return_value=Response(200, json=SINGLE_SERVICE_TYPE_RESPONSE)
    )

    response = await verified_authenticated_client.get("/api/pco/status")
    assert response.status_code == 200
    body = response.json()
    assert body["service_type_id"] == "111"
    assert body["service_type_name"] == "Sunday Morning"


@respx.mock
async def test_pco_status_service_type_pco_api_failure(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """When PCO API fails for service type name, service_type_id is set but name is None."""
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = user_result.scalar_one()

    conn = PcoConnection(
        church_id=user.church_id,
        auth_method="api_key",
        app_id_encrypted=encrypt("test_app_id"),
        secret_encrypted=encrypt("test_secret"),
        status="active",
        last_successful_call_at=datetime.now(timezone.utc),
    )
    db.add(conn)

    church_result = await db.execute(select(Church).where(Church.id == user.church_id))
    church = church_result.scalar_one()
    church.pco_service_type_id = "111"
    await db.flush()

    # Simulate PCO API 500 error
    respx.get(f"{PCO_BASE}/services/v2/service_types/111").mock(
        return_value=Response(500, json={"errors": [{"status": "500", "title": "Server Error"}]})
    )

    response = await verified_authenticated_client.get("/api/pco/status")
    assert response.status_code == 200
    body = response.json()
    assert body["service_type_id"] == "111"
    assert body["service_type_name"] is None
