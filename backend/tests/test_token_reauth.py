"""Tests for expired-refresh-token (invalid_grant) handling.

Covers refresh_spotify_token / refresh_youtube_token branching on 400
invalid_grant vs. other transient failures (Task 1, 2).

Outbound Spotify/Google HTTP calls are mocked via respx. asyncio_mode = "auto"
(set in pyproject.toml) runs all async test functions automatically.
"""

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.church import Church
from app.models.streaming_connection import StreamingConnection
from app.services.streaming_service import (
    SpotifyTokenError,
    TokenReauthRequiredError,
    YouTubeTokenError,
    refresh_spotify_token,
    refresh_youtube_token,
)
from app.utils.encryption import decrypt, encrypt

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


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
