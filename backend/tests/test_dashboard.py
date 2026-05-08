"""Dashboard endpoint and require_auth dependency tests."""

import uuid
from datetime import datetime, timedelta, timezone

import respx
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.church import Church
from app.models.church_user import ChurchUser
from app.models.pco_connection import PcoConnection
from app.models.song_mapping import SongMapping
from app.models.streaming_connection import StreamingConnection
from app.models.sync_log import SyncLog
from app.utils.encryption import encrypt
from tests.fixtures.pco_responses import PLAN_ITEMS_WITH_SONGS_RESPONSE, UPCOMING_PLANS_RESPONSE

PCO_BASE = "https://api.planningcenteronline.com"

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


async def test_dashboard_returns_church_name(verified_authenticated_client: AsyncClient, db: AsyncSession):
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


async def test_dashboard_pco_connected(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """When PCO connection exists, pco_connected should be True."""
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
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


async def test_dashboard_service_type_selected(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """When service_type_id is set on church, service_type_selected is True."""
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = user_result.scalar_one()

    church_result = await db.execute(select(Church).where(Church.id == user.church_id))
    church = church_result.scalar_one()
    church.pco_service_type_id = "111"
    await db.flush()

    response = await verified_authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["service_type_selected"] is True


async def test_dashboard_recent_syncs_max_5(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """Recent syncs returns at most 5 entries, ordered by most recent first."""
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
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


# ---------------------------------------------------------------------------
# unmatched_song_count — per-platform matching state (issue #47)
# ---------------------------------------------------------------------------


async def _setup_pco_and_plans_mocks(db: AsyncSession) -> uuid.UUID:
    """Set up an active PCO connection + service_type and mock PCO HTTP for two plans."""
    user_result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = user_result.scalar_one()
    church_id = user.church_id

    db.add(
        PcoConnection(
            church_id=church_id,
            auth_method="api_key",
            app_id_encrypted=encrypt("test_app_id"),
            secret_encrypted=encrypt("test_secret"),
            status="active",
        )
    )
    church_result = await db.execute(select(Church).where(Church.id == church_id))
    church = church_result.scalar_one()
    church.pco_service_type_id = "111"
    await db.flush()

    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans").mock(
        return_value=Response(200, json=UPCOMING_PLANS_RESPONSE)
    )
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1002/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    return church_id


def _make_streaming_connection(church_id: uuid.UUID, platform: str, status: str = "active") -> StreamingConnection:
    return StreamingConnection(
        church_id=church_id,
        platform=platform,
        access_token_encrypted=encrypt(f"{platform}_access"),
        refresh_token_encrypted=encrypt(f"{platform}_refresh"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        external_user_id=f"{platform}_user",
        status=status,
    )


def _make_song_mapping(church_id: uuid.UUID, pco_song_id: str, platform: str) -> SongMapping:
    return SongMapping(
        church_id=church_id,
        pco_song_id=pco_song_id,
        pco_song_title=pco_song_id,
        platform=platform,
        track_id=f"{platform}:track:{pco_song_id}",
        track_title=pco_song_id,
    )


@respx.mock
async def test_dashboard_unmatched_counts_song_missing_on_one_platform(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """A song mapped on Spotify but not YouTube counts as unmatched when both platforms are connected."""
    church_id = await _setup_pco_and_plans_mocks(db)
    db.add(_make_streaming_connection(church_id, "spotify"))
    db.add(_make_streaming_connection(church_id, "youtube"))
    db.add(_make_song_mapping(church_id, "song-1", "spotify"))
    db.add(_make_song_mapping(church_id, "song-2", "spotify"))
    await db.flush()

    response = await verified_authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    # Both plans share the same two songs; each song is unmatched on YouTube.
    # Plan 1001 has 2 unmatched, plan 1002 has 2 unmatched → total 4.
    assert body["unmatched_song_count"] == 4
    for plan in body["upcoming_plans"]:
        for song in plan["songs"]:
            assert song["matched"] is False


@respx.mock
async def test_dashboard_unmatched_zero_when_song_matched_on_all_connected(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """A song mapped on every connected platform counts as matched."""
    church_id = await _setup_pco_and_plans_mocks(db)
    db.add(_make_streaming_connection(church_id, "spotify"))
    db.add(_make_streaming_connection(church_id, "youtube"))
    for song_id in ("song-1", "song-2"):
        db.add(_make_song_mapping(church_id, song_id, "spotify"))
        db.add(_make_song_mapping(church_id, song_id, "youtube"))
    await db.flush()

    response = await verified_authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["unmatched_song_count"] == 0
    for plan in body["upcoming_plans"]:
        for song in plan["songs"]:
            assert song["matched"] is True


@respx.mock
async def test_dashboard_unmatched_ignores_mappings_for_disconnected_platforms(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """Mappings for platforms the church is not connected to do not count toward 'matched'."""
    church_id = await _setup_pco_and_plans_mocks(db)
    db.add(_make_streaming_connection(church_id, "spotify"))
    # Only YouTube mappings exist, but YouTube is not connected.
    for song_id in ("song-1", "song-2"):
        db.add(_make_song_mapping(church_id, song_id, "youtube"))
    await db.flush()

    response = await verified_authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    # Spotify is the only connected platform and has zero mappings → all songs unmatched.
    assert body["unmatched_song_count"] == 4


@respx.mock
async def test_dashboard_unmatched_zero_when_no_platforms_connected(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """With no connected platforms there's no matching to do — count is 0."""
    church_id = await _setup_pco_and_plans_mocks(db)
    # No StreamingConnection rows at all.
    db.add(_make_song_mapping(church_id, "song-1", "spotify"))  # stale mapping, ignored
    await db.flush()

    response = await verified_authenticated_client.get("/api/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["unmatched_song_count"] == 0
    for plan in body["upcoming_plans"]:
        for song in plan["songs"]:
            assert song["matched"] is True
