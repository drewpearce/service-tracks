"""Tests for GET /api/plans endpoint."""

import respx
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.church import Church
from app.models.church_user import ChurchUser
from app.models.pco_connection import PcoConnection
from app.models.song_mapping import SongMapping
from app.utils.encryption import encrypt
from tests.fixtures.pco_responses import PLAN_ITEMS_WITH_SONGS_RESPONSE, UPCOMING_PLANS_RESPONSE

PCO_BASE = "https://api.planningcenteronline.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def setup_pco_connection(db: AsyncSession, church_id) -> None:
    conn = PcoConnection(
        church_id=church_id,
        auth_method="api_key",
        app_id_encrypted=encrypt("test_app_id"),
        secret_encrypted=encrypt("test_secret"),
        status="active",
    )
    db.add(conn)
    church_result = await db.execute(select(Church).where(Church.id == church_id))
    church = church_result.scalar_one()
    church.pco_service_type_id = "111"
    await db.flush()


# ---------------------------------------------------------------------------
# GET /api/plans tests
# ---------------------------------------------------------------------------


async def test_get_plans_unauthenticated(client: AsyncClient):
    """Unauthenticated request returns 401."""
    response = await client.get("/api/plans")
    assert response.status_code == 401


async def test_get_plans_unverified_email(authenticated_client: AsyncClient):
    """Unverified user gets 403."""
    response = await authenticated_client.get("/api/plans")
    assert response.status_code == 403
    assert authenticated_client.cookies.get("csrf_token") is not None


async def test_get_plans_no_pco_connection(verified_authenticated_client: AsyncClient):
    """Returns empty plans list when no PCO connection."""
    response = await verified_authenticated_client.get("/api/plans")
    assert response.status_code == 200
    body = response.json()
    assert body["plans"] == []


@respx.mock
async def test_get_plans_returns_plans_with_match_status(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """Returns plans with song match status when PCO is connected."""
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = user_result.scalar_one()
    await setup_pco_connection(db, user.church_id)

    # Add a mapping for song-1 so it's matched
    db.add(
        SongMapping(
            church_id=user.church_id,
            pco_song_id="song-1",
            pco_song_title="How Great Is Our God",
            platform="spotify",
            track_id="spotify:track:abc",
            track_title="How Great Is Our God",
        )
    )
    await db.flush()

    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans").mock(
        return_value=Response(200, json=UPCOMING_PLANS_RESPONSE)
    )
    # Both plans fetch songs
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1002/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )

    response = await verified_authenticated_client.get("/api/plans")
    assert response.status_code == 200
    body = response.json()
    assert len(body["plans"]) == 2

    # Check first plan
    plan = body["plans"][0]
    assert plan["pco_plan_id"] == "1001"
    assert "songs" in plan
    # song-1 should be matched, song-2 unmatched
    songs_by_id = {s["pco_song_id"]: s for s in plan["songs"]}
    assert songs_by_id["song-1"]["matched"] is True
    assert songs_by_id["song-2"]["matched"] is False
    assert plan["unmatched_count"] == 1
