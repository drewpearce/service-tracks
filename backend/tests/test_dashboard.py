"""Dashboard endpoint and require_auth dependency tests."""

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.church import Church
from app.models.church_user import ChurchUser
from app.models.pco_connection import PcoConnection
from app.models.sync_log import SyncLog
from app.utils.encryption import encrypt

# ---------------------------------------------------------------------------
# require_auth dependency tests
# ---------------------------------------------------------------------------


async def test_require_auth_unauthenticated(client: AsyncClient):
    """Unauthenticated request returns 401."""
    # GET /api/health to get a CSRF cookie, then hit dashboard
    await client.get("/api/health")
    response = await client.get("/api/dashboard")
    assert response.status_code == 401


async def test_require_auth_authenticated_unverified(
    authenticated_client: AsyncClient,
):
    """Authenticated but unverified user can access /api/dashboard (200, not 403)."""
    response = await authenticated_client.get("/api/dashboard")
    assert response.status_code == 200


async def test_require_auth_authenticated_verified(
    verified_authenticated_client: AsyncClient,
):
    """Verified user can also access /api/dashboard."""
    response = await verified_authenticated_client.get("/api/dashboard")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/dashboard tests
# ---------------------------------------------------------------------------


async def test_dashboard_returns_church_name(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """Dashboard response includes the correct church name."""
    response = await verified_authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert "church_name" in body
    assert body["church_name"] == "Verified Church"


async def test_dashboard_pco_not_connected(
    verified_authenticated_client: AsyncClient,
):
    """When PCO is not connected, pco_connected should be False."""
    response = await verified_authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["pco_connected"] is False
    assert body["service_type_selected"] is False
    assert body["upcoming_plans"] == []


async def test_dashboard_pco_connected(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """When PCO connection exists, pco_connected should be True."""
    user_result = await db.execute(
        select(ChurchUser).where(ChurchUser.email == "verified@example.com")
    )
    user = user_result.scalar_one()

    conn = PcoConnection(
        church_id=user.church_id,
        auth_method="api_key",
        app_id_encrypted=encrypt("test_app_id"),
        secret_encrypted=encrypt("test_secret"),
        status="active",
    )
    db.add(conn)
    await db.flush()

    response = await verified_authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["pco_connected"] is True


async def test_dashboard_service_type_selected(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """When service_type_id is set on church, service_type_selected is True."""
    user_result = await db.execute(
        select(ChurchUser).where(ChurchUser.email == "verified@example.com")
    )
    user = user_result.scalar_one()

    church_result = await db.execute(select(Church).where(Church.id == user.church_id))
    church = church_result.scalar_one()
    church.pco_service_type_id = "111"
    await db.flush()

    response = await verified_authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["service_type_selected"] is True


async def test_dashboard_recent_syncs_max_5(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """Recent syncs returns at most 5 entries, ordered by most recent first."""
    user_result = await db.execute(
        select(ChurchUser).where(ChurchUser.email == "verified@example.com")
    )
    user = user_result.scalar_one()

    now = datetime.now(timezone.utc)
    for i in range(7):
        sl = SyncLog(
            church_id=user.church_id,
            sync_trigger="manual",
            status="synced",
            songs_total=5,
            songs_matched=5,
            songs_unmatched=0,
            started_at=now,
            completed_at=now,
        )
        db.add(sl)
    await db.flush()

    response = await verified_authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert len(body["recent_syncs"]) == 5


async def test_dashboard_unverified_user_gets_200(
    authenticated_client: AsyncClient,
):
    """Unverified user can access dashboard — setup checklist renders for unverified users."""
    response = await authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert "pco_connected" in body
    assert "upcoming_plans" in body
