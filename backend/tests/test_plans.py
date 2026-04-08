"""Plans router integration tests — Epic 7.

Tests use real PostgreSQL (service_tracks_test DB) with per-test transaction rollback.
Outbound PCO and Spotify HTTP calls are mocked via respx.
asyncio_mode = "auto" (set in pyproject.toml) makes all async test functions run automatically.
"""

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
from app.utils.encryption import encrypt
from tests.fixtures.pco_responses import PLAN_ITEMS_WITH_SONGS_RESPONSE
from tests.fixtures.spotify_responses import (
    SPOTIFY_CREATE_PLAYLIST_RESPONSE,
    SPOTIFY_REPLACE_TRACKS_RESPONSE,
)

PCO_BASE = "https://api.planningcenteronline.com"
SPOTIFY_BASE = "https://api.spotify.com/v1"

PCO_PLAN_RESPONSE = {
    "data": {
        "id": "1001",
        "type": "Plan",
        "attributes": {
            "title": "Sunday Service",
            "sort_date": "2026-03-22",
            "series_title": None,
        },
    }
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def get_verified_church_id(db: AsyncSession) -> uuid.UUID:
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = result.scalar_one()
    return user.church_id


async def setup_church_for_sync(db: AsyncSession, church_id: uuid.UUID) -> None:
    """Set up a church with PCO connection, Spotify connection, and song mappings."""
    pco_conn = PcoConnection(
        church_id=church_id,
        auth_method="api_key",
        app_id_encrypted=encrypt("test_app_id"),
        secret_encrypted=encrypt("test_secret"),
        status="active",
    )
    db.add(pco_conn)

    church_result = await db.execute(select(Church).where(Church.id == church_id))
    church = church_result.scalar_one()
    church.pco_service_type_id = "111"

    streaming_conn = StreamingConnection(
        church_id=church_id,
        platform="spotify",
        access_token_encrypted=encrypt("test_access_token"),
        refresh_token_encrypted=encrypt("test_refresh_token"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        external_user_id="spotify_user_123",
        status="active",
    )
    db.add(streaming_conn)

    db.add(
        SongMapping(
            church_id=church_id,
            pco_song_id="song-1",
            pco_song_title="How Great Is Our God",
            platform="spotify",
            track_id="spotify:track:track1",
            track_title="How Great Is Our God",
        )
    )
    db.add(
        SongMapping(
            church_id=church_id,
            pco_song_id="song-2",
            pco_song_title="Amazing Grace",
            platform="spotify",
            track_id="spotify:track:track2",
            track_title="Amazing Grace",
        )
    )
    await db.flush()


# ---------------------------------------------------------------------------
# Test 1: Happy path
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_endpoint_returns_result(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    church_id = await get_verified_church_id(db)
    await setup_church_for_sync(db, church_id)

    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001").mock(
        return_value=Response(200, json=PCO_PLAN_RESPONSE)
    )
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    respx.get(f"{SPOTIFY_BASE}/me/playlists").mock(
        return_value=Response(200, json={"items": [], "total": 0})
    )
    respx.post(f"{SPOTIFY_BASE}/users/spotify_user_123/playlists").mock(
        return_value=Response(201, json=SPOTIFY_CREATE_PLAYLIST_RESPONSE)
    )
    respx.put(f"{SPOTIFY_BASE}/playlists/playlist123/tracks").mock(
        return_value=Response(201, json=SPOTIFY_REPLACE_TRACKS_RESPONSE)
    )

    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    response = await verified_authenticated_client.post(
        "/api/plans/1001/sync",
        headers={"x-csrf-token": csrf},
    )

    assert response.status_code == 200
    body = response.json()
    assert "sync_status" in body
    assert "songs_total" in body
    assert "songs_matched" in body
    assert "platforms" in body
    assert body["sync_status"] == "synced"
    assert body["songs_total"] == 2


# ---------------------------------------------------------------------------
# Test 2: Rate limiting — 6/hour limit
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_endpoint_rate_limited(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    church_id = await get_verified_church_id(db)
    await setup_church_for_sync(db, church_id)

    # Use side_effect to return valid responses for first 6 calls
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001").mock(
        return_value=Response(200, json=PCO_PLAN_RESPONSE)
    )
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    respx.get(f"{SPOTIFY_BASE}/me/playlists").mock(
        return_value=Response(200, json={"items": [], "total": 0})
    )
    respx.post(f"{SPOTIFY_BASE}/users/spotify_user_123/playlists").mock(
        return_value=Response(201, json=SPOTIFY_CREATE_PLAYLIST_RESPONSE)
    )
    respx.put(f"{SPOTIFY_BASE}/playlists/playlist123/tracks").mock(
        return_value=Response(201, json=SPOTIFY_REPLACE_TRACKS_RESPONSE)
    )

    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    headers = {"x-csrf-token": csrf}

    statuses = []
    for _ in range(7):
        resp = await verified_authenticated_client.post("/api/plans/1001/sync", headers=headers)
        statuses.append(resp.status_code)

    # First 6 should succeed, 7th should be rate limited
    assert statuses[:6] == [200, 200, 200, 200, 200, 200]
    assert statuses[6] == 429


# ---------------------------------------------------------------------------
# Test 3: Unauthenticated request
# ---------------------------------------------------------------------------


async def test_sync_endpoint_requires_auth(client: AsyncClient):
    # Get CSRF cookie first
    await client.get("/api/health")
    csrf = client.cookies.get("csrf_token", "")
    response = await client.post(
        "/api/plans/1001/sync",
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Test 4: Unverified email
# ---------------------------------------------------------------------------


async def test_sync_endpoint_requires_verified_email(authenticated_client: AsyncClient):
    csrf = authenticated_client.cookies.get("csrf_token", "")
    response = await authenticated_client.post(
        "/api/plans/1001/sync",
        headers={"x-csrf-token": csrf},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "email_not_verified"


# ---------------------------------------------------------------------------
# Test 5: Missing CSRF token
# ---------------------------------------------------------------------------


async def test_sync_endpoint_requires_csrf(verified_authenticated_client: AsyncClient):
    # Omit the x-csrf-token header
    response = await verified_authenticated_client.post("/api/plans/1001/sync")
    assert response.status_code == 403
