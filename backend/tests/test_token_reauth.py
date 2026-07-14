"""Tests for expired-refresh-token (invalid_grant) handling.

Covers:
 - refresh_spotify_token / refresh_youtube_token branching on 400 invalid_grant
   vs. other transient failures (Task 1, 2).
 - GET /api/streaming/status passthrough of status="needs_reauth" (Task 4).

Outbound Spotify/Google HTTP calls are mocked via respx. asyncio_mode = "auto"
(set in pyproject.toml) runs all async test functions automatically.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
import respx
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.church import Church
from app.models.church_user import ChurchUser
from app.models.pco_connection import PcoConnection
from app.models.streaming_connection import StreamingConnection
from app.services.streaming_service import (
    SpotifyTokenError,
    TokenReauthRequiredError,
    YouTubeTokenError,
    refresh_spotify_token,
    refresh_youtube_token,
)
from app.services.sync_service import sync_plan
from app.utils.encryption import decrypt, encrypt
from tests.fixtures.pco_responses import PLAN_ITEMS_WITH_SONGS_RESPONSE

PCO_BASE = "https://api.planningcenteronline.com"

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


async def get_verified_user_church_id(db: AsyncSession) -> uuid.UUID:
    """Return the church_id of the verified test user (see verified_authenticated_client)."""
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    return result.scalar_one().church_id


@pytest_asyncio.fixture
async def church_id(db: AsyncSession) -> uuid.UUID:
    """Create a minimal church and return its UUID."""
    unique_slug = f"test-reauth-church-{uuid.uuid4().hex[:8]}"
    church = Church(name="Test Reauth Church", slug=unique_slug)
    db.add(church)
    await db.flush()
    return church.id


async def make_streaming_connection(
    db: AsyncSession,
    church_id: uuid.UUID,
    platform: str,
) -> StreamingConnection:
    """Insert an active StreamingConnection row with encrypted tokens."""
    conn = StreamingConnection(
        church_id=church_id,
        platform=platform,
        access_token_encrypted=encrypt("a"),
        refresh_token_encrypted=encrypt("r"),
        token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        external_user_id="u",
        status="active",
    )
    db.add(conn)
    await db.flush()
    return conn


@pytest_asyncio.fixture
async def spotify_connection(db: AsyncSession, church_id: uuid.UUID) -> StreamingConnection:
    return await make_streaming_connection(db, church_id, platform="spotify")


@pytest_asyncio.fixture
async def youtube_connection(db: AsyncSession, church_id: uuid.UUID) -> StreamingConnection:
    return await make_streaming_connection(db, church_id, platform="youtube")


# ---------------------------------------------------------------------------
# refresh_spotify_token
# ---------------------------------------------------------------------------


@respx.mock
async def test_spotify_refresh_invalid_grant_sets_needs_reauth(
    db: AsyncSession, spotify_connection: StreamingConnection
):
    route = respx.post("https://accounts.spotify.com/api/token").mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )
    original_refresh = spotify_connection.refresh_token_encrypted

    with pytest.raises(TokenReauthRequiredError):
        await refresh_spotify_token(db, spotify_connection)

    assert route.call_count == 1  # no retry
    assert spotify_connection.status == "needs_reauth"
    # token bytes preserved (not cleared)
    assert spotify_connection.refresh_token_encrypted == original_refresh
    assert decrypt(spotify_connection.refresh_token_encrypted)  # still decryptable


@respx.mock
async def test_spotify_refresh_transient_error_sets_error(db: AsyncSession, spotify_connection: StreamingConnection):
    respx.post("https://accounts.spotify.com/api/token").mock(
        return_value=httpx.Response(500, json={"error": "server_error"})
    )

    with pytest.raises(SpotifyTokenError):
        await refresh_spotify_token(db, spotify_connection)
    assert spotify_connection.status == "error"


# ---------------------------------------------------------------------------
# refresh_youtube_token
# ---------------------------------------------------------------------------


@respx.mock
async def test_youtube_refresh_invalid_grant_sets_needs_reauth(
    db: AsyncSession, youtube_connection: StreamingConnection
):
    route = respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )

    with pytest.raises(TokenReauthRequiredError):
        await refresh_youtube_token(db, youtube_connection)

    assert route.call_count == 1
    assert youtube_connection.status == "needs_reauth"


@respx.mock
async def test_youtube_refresh_transient_error_sets_error(db: AsyncSession, youtube_connection: StreamingConnection):
    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=httpx.Response(503, json={"error": "unavailable"})
    )

    with pytest.raises(YouTubeTokenError):
        await refresh_youtube_token(db, youtube_connection)
    assert youtube_connection.status == "error"


# ---------------------------------------------------------------------------
# GET /api/streaming/status passthrough
# ---------------------------------------------------------------------------


async def test_streaming_status_exposes_needs_reauth(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_user_church_id(db)
    conn = StreamingConnection(
        church_id=church_id,
        platform="spotify",
        access_token_encrypted=encrypt("a"),
        refresh_token_encrypted=encrypt("r"),
        token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        external_user_id="spotify_user_needs_reauth",
        status="needs_reauth",
    )
    db.add(conn)
    await db.flush()

    resp = await verified_authenticated_client.get("/api/streaming/status")
    assert resp.status_code == 200
    conns = resp.json()["connections"]
    spotify = next(c for c in conns if c["platform"] == "spotify")
    assert spotify["status"] == "needs_reauth"
    assert spotify["connected"] is False  # connected semantics unchanged


# ---------------------------------------------------------------------------
# sync_plan — token dies mid-sync (Task 3)
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_plan_skips_connection_needing_reauth(db: AsyncSession, verified_authenticated_client: AsyncClient):
    """A token that expires mid-sync must not surface as a generic sync error."""
    church_id = await get_verified_user_church_id(db)

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

    # Active connection whose token is already expired — the adapter will try
    # to refresh it on first use, mid-sync, and the refresh will fail with
    # invalid_grant.
    streaming_conn = StreamingConnection(
        church_id=church_id,
        platform="spotify",
        access_token_encrypted=encrypt("test_access_token"),
        refresh_token_encrypted=encrypt("test_refresh_token"),
        token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        external_user_id="spotify_user_123",
        status="active",
    )
    db.add(streaming_conn)
    await db.flush()

    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    respx.post("https://accounts.spotify.com/api/token").mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )

    result = await sync_plan(db, church_id, "1001", "manual", plan_date=date(2026, 3, 22), plan_title="Sunday Service")

    # sync_plan must return normally — no unhandled TokenReauthRequiredError.
    assert len(result.platforms) == 1
    platform_result = result.platforms[0]
    assert platform_result.platform == "spotify"
    # Reconnection is a distinct, actionable outcome — not a generic transient error.
    assert platform_result.sync_status == "skipped"
    assert platform_result.error_message == "reconnection_required"
    assert result.sync_status != "error"

    conn_result = await db.execute(select(StreamingConnection).where(StreamingConnection.id == streaming_conn.id))
    conn = conn_result.scalar_one()
    assert conn.status == "needs_reauth"
