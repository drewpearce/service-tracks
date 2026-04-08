"""Unit tests for SpotifyAdapter using respx for HTTP mocking."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
import respx
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.spotify_adapter import (
    SpotifyAdapter,
    SpotifyAuthError,
    SpotifyForbiddenError,
    SpotifyRateLimitError,
)
from app.models.streaming_connection import StreamingConnection
from app.utils.encryption import decrypt, encrypt
from tests.fixtures.spotify_responses import (
    SPOTIFY_CREATE_PLAYLIST_RESPONSE,
    SPOTIFY_PLAYLIST_TRACKS_RESPONSE,
    SPOTIFY_SEARCH_EMPTY_RESPONSE,
    SPOTIFY_SEARCH_RESPONSE,
    SPOTIFY_TOKEN_REFRESH_WITH_NEW_REFRESH,
    SPOTIFY_TOKEN_REFRESH_WITHOUT_NEW_REFRESH,
    SPOTIFY_USER_PROFILE_RESPONSE,
)

# ---------------------------------------------------------------------------
# Helper fixture
# ---------------------------------------------------------------------------


async def make_streaming_connection(
    db: AsyncSession,
    church_id: uuid.UUID,
    token_expires_at: datetime | None = None,
    access_token: str = "test_access_token",
    refresh_token: str = "test_refresh_token",
) -> StreamingConnection:
    """Insert a StreamingConnection row with encrypted tokens and configurable expiry."""
    if token_expires_at is None:
        token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    conn = StreamingConnection(
        church_id=church_id,
        platform="spotify",
        access_token_encrypted=encrypt(access_token),
        refresh_token_encrypted=encrypt(refresh_token),
        token_expires_at=token_expires_at,
        external_user_id="churchspotify123",
        status="active",
    )
    db.add(conn)
    await db.flush()
    return conn


@pytest_asyncio.fixture
async def church_id(db: AsyncSession) -> uuid.UUID:
    """Create a minimal church and return its UUID."""
    from app.models.church import Church

    unique_slug = f"test-spotify-church-{uuid.uuid4().hex[:8]}"
    church = Church(name="Test Spotify Church", slug=unique_slug)
    db.add(church)
    await db.flush()
    return church.id


# ---------------------------------------------------------------------------
# Tests: happy path adapter methods
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_search_tracks_success(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = SpotifyAdapter(conn, db)

    respx.get("https://api.spotify.com/v1/search").mock(
        return_value=Response(200, json=SPOTIFY_SEARCH_RESPONSE)
    )

    results = await adapter.search_tracks("How Great Is Our God")

    assert len(results) == 2
    first = results[0]
    assert first.track_id == "spotify:track:4iV5W9uYEdYUVa79Axb7Rh"
    assert first.title == "How Great Is Our God"
    assert first.artist == "Chris Tomlin"
    assert first.album == "Arriving"
    assert first.image_url == "https://i.scdn.co/image/abc123"
    assert first.duration_ms == 253000

    second = results[1]
    assert second.artist == "John Newton, Various Artists"


@pytest.mark.asyncio
@respx.mock
async def test_search_tracks_empty(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = SpotifyAdapter(conn, db)

    respx.get("https://api.spotify.com/v1/search").mock(
        return_value=Response(200, json=SPOTIFY_SEARCH_EMPTY_RESPONSE)
    )

    results = await adapter.search_tracks("nonexistent track xyz")
    assert results == []


@pytest.mark.asyncio
@respx.mock
async def test_create_playlist_success(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = SpotifyAdapter(conn, db)

    respx.post("https://api.spotify.com/v1/users/churchspotify123/playlists").mock(
        return_value=Response(200, json=SPOTIFY_CREATE_PLAYLIST_RESPONSE)
    )

    playlist = await adapter.create_playlist(
        name="Sunday Morning Worship",
        description="Songs for this week",
    )

    assert playlist.external_id == "playlist123"
    assert playlist.url == "https://open.spotify.com/playlist/playlist123"
    assert playlist.name == "Sunday Morning Worship"


@pytest.mark.asyncio
@respx.mock
async def test_get_playlist_tracks_success(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = SpotifyAdapter(conn, db)

    respx.get("https://api.spotify.com/v1/playlists/playlist123/tracks").mock(
        return_value=Response(200, json=SPOTIFY_PLAYLIST_TRACKS_RESPONSE)
    )

    tracks = await adapter.get_playlist_tracks("playlist123")

    # Should return 2 tracks (None track filtered out)
    assert len(tracks) == 2
    assert "spotify:track:4iV5W9uYEdYUVa79Axb7Rh" in tracks
    assert "spotify:track:7ouMYWpwJ422jRcDASZB7P" in tracks


@pytest.mark.asyncio
@respx.mock
async def test_replace_playlist_tracks_success(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = SpotifyAdapter(conn, db)

    track_ids = [
        "spotify:track:4iV5W9uYEdYUVa79Axb7Rh",
        "spotify:track:7ouMYWpwJ422jRcDASZB7P",
    ]

    put_mock = respx.put("https://api.spotify.com/v1/playlists/playlist123/tracks").mock(
        return_value=Response(200, json={"snapshot_id": "abc"})
    )

    await adapter.replace_playlist_tracks("playlist123", track_ids)

    assert put_mock.called
    import json
    request_body = json.loads(put_mock.calls[0].request.content)
    assert request_body["uris"] == track_ids


@pytest.mark.asyncio
async def test_get_playlist_url(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = SpotifyAdapter(conn, db)

    url = await adapter.get_playlist_url("playlist123")
    assert url == "https://open.spotify.com/playlist/playlist123"


@pytest.mark.asyncio
@respx.mock
async def test_validate_connection_success(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = SpotifyAdapter(conn, db)

    respx.get("https://api.spotify.com/v1/me").mock(
        return_value=Response(200, json=SPOTIFY_USER_PROFILE_RESPONSE)
    )

    result = await adapter.validate_connection()
    assert result is True


@pytest.mark.asyncio
@respx.mock
async def test_validate_connection_invalid(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = SpotifyAdapter(conn, db)

    respx.get("https://api.spotify.com/v1/me").mock(
        return_value=Response(401, json={"error": {"status": 401, "message": "Unauthorized"}})
    )

    result = await adapter.validate_connection()
    assert result is False


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_401_marks_connection_as_error(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = SpotifyAdapter(conn, db)

    respx.get("https://api.spotify.com/v1/search").mock(
        return_value=Response(401, json={"error": {"status": 401, "message": "Unauthorized"}})
    )

    with pytest.raises(SpotifyAuthError):
        await adapter.search_tracks("test query")

    assert conn.status == "error"


@pytest.mark.asyncio
@respx.mock
async def test_429_raises_rate_limit_error(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = SpotifyAdapter(conn, db)

    respx.get("https://api.spotify.com/v1/search").mock(
        return_value=Response(
            429,
            json={"error": {"status": 429, "message": "Too Many Requests"}},
            headers={"Retry-After": "30"},
        )
    )

    with pytest.raises(SpotifyRateLimitError) as exc_info:
        await adapter.search_tracks("test query")

    assert exc_info.value.retry_after == 30


@pytest.mark.asyncio
@respx.mock
async def test_403_raises_forbidden_error(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = SpotifyAdapter(conn, db)

    respx.get("https://api.spotify.com/v1/search").mock(
        return_value=Response(403, json={"error": {"status": 403, "message": "Forbidden"}})
    )

    with pytest.raises(SpotifyForbiddenError):
        await adapter.search_tracks("test query")


# ---------------------------------------------------------------------------
# Tests: token refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_token_refresh_with_new_refresh_token(db: AsyncSession, church_id: uuid.UUID):
    """When Spotify returns a new refresh token, it should be stored."""
    # Token expires in 1 minute (within the 5-minute buffer)
    soon_expiry = datetime.now(timezone.utc) + timedelta(minutes=1)
    conn = await make_streaming_connection(
        db,
        church_id,
        token_expires_at=soon_expiry,
        refresh_token="original_refresh_token",
    )
    adapter = SpotifyAdapter(conn, db)

    # Mock token refresh
    respx.post("https://accounts.spotify.com/api/token").mock(
        return_value=Response(200, json=SPOTIFY_TOKEN_REFRESH_WITH_NEW_REFRESH)
    )
    # Mock the actual API call
    respx.get("https://api.spotify.com/v1/search").mock(
        return_value=Response(200, json=SPOTIFY_SEARCH_EMPTY_RESPONSE)
    )

    await adapter.search_tracks("test")

    # Check connection was updated with new tokens
    assert decrypt(conn.access_token_encrypted) == SPOTIFY_TOKEN_REFRESH_WITH_NEW_REFRESH["access_token"]
    assert decrypt(conn.refresh_token_encrypted) == SPOTIFY_TOKEN_REFRESH_WITH_NEW_REFRESH["refresh_token"]
    assert conn.token_expires_at > soon_expiry
    assert conn.status == "active"


@pytest.mark.asyncio
@respx.mock
async def test_token_refresh_without_new_refresh_token(db: AsyncSession, church_id: uuid.UUID):
    """CRITICAL: When Spotify omits refresh_token, the original refresh token must be preserved."""
    original_refresh_token = "original_refresh_token_to_preserve"
    soon_expiry = datetime.now(timezone.utc) + timedelta(minutes=1)
    conn = await make_streaming_connection(
        db,
        church_id,
        token_expires_at=soon_expiry,
        refresh_token=original_refresh_token,
    )
    adapter = SpotifyAdapter(conn, db)

    # Mock token refresh — response does NOT include refresh_token
    respx.post("https://accounts.spotify.com/api/token").mock(
        return_value=Response(200, json=SPOTIFY_TOKEN_REFRESH_WITHOUT_NEW_REFRESH)
    )
    # Mock the actual API call
    respx.get("https://api.spotify.com/v1/search").mock(
        return_value=Response(200, json=SPOTIFY_SEARCH_EMPTY_RESPONSE)
    )

    await adapter.search_tracks("test")

    # Access token should be updated
    assert decrypt(conn.access_token_encrypted) == SPOTIFY_TOKEN_REFRESH_WITHOUT_NEW_REFRESH["access_token"]
    # Refresh token MUST be preserved — this is the critical behavior
    assert decrypt(conn.refresh_token_encrypted) == original_refresh_token


@pytest.mark.asyncio
@respx.mock
async def test_no_refresh_when_token_not_expiring(db: AsyncSession, church_id: uuid.UUID):
    """When token has 30+ minutes left, no refresh should be triggered."""
    # Token expires in 30 minutes (outside the 5-minute buffer)
    conn = await make_streaming_connection(
        db,
        church_id,
        token_expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    adapter = SpotifyAdapter(conn, db)

    token_route = respx.post("https://accounts.spotify.com/api/token")
    respx.get("https://api.spotify.com/v1/search").mock(
        return_value=Response(200, json=SPOTIFY_SEARCH_EMPTY_RESPONSE)
    )

    await adapter.search_tracks("test")

    # Token refresh endpoint should NOT have been called
    assert not token_route.called
