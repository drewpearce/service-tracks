"""Unit tests for YouTubeAdapter.

Search tests mock ytmusicapi.YTMusic.search directly (unauthenticated, no HTTP).
All other tests use respx to mock the YouTube Data API v3.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
import respx
from httpx import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.youtube_adapter import YouTubeAdapter
from app.models.search_cache import SearchCache
from app.models.streaming_connection import StreamingConnection
from app.services.streaming_service import refresh_youtube_token
from app.utils.encryption import decrypt, encrypt

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


# ytmusicapi-shaped search results (filter='songs')
FAKE_YTM_RESULTS = [
    {
        "videoId": "abc123XYZ01",
        "title": "How Great Is Our God",
        "artists": [{"name": "Chris Tomlin", "id": "UC_tomlin"}],
        "album": {"name": "Arriving", "id": "MPR_arriving"},
        "thumbnails": [
            {"url": "https://lh3.googleusercontent.com/thumb_small.jpg", "width": 60, "height": 60},
            {"url": "https://lh3.googleusercontent.com/thumb_large.jpg", "width": 226, "height": 226},
        ],
        "category": "Songs",
    },
    {
        "videoId": "def456UVW02",
        "title": "Amazing Grace",
        "artists": [{"name": "Various Artists", "id": "UC_va"}],
        "album": None,
        "thumbnails": [
            {"url": "https://lh3.googleusercontent.com/thumb2.jpg", "width": 60, "height": 60},
        ],
        "category": "Songs",
    },
]

YOUTUBE_CREATE_PLAYLIST_RESPONSE = {
    "id": "PL_ytplaylist123",
    "snippet": {"title": "Sunday Morning Worship", "description": "Songs for this week"},
    "status": {"privacyStatus": "public"},
}

YOUTUBE_PLAYLIST_ITEMS_RESPONSE = {
    "items": [
        {
            "id": "PLI_item1",
            "contentDetails": {"videoId": "abc123XYZ01"},
        },
        {
            "id": "PLI_item2",
            "contentDetails": {"videoId": "def456UVW02"},
        },
    ]
}


async def make_streaming_connection(
    db: AsyncSession,
    church_id: uuid.UUID,
    token_expires_at: datetime | None = None,
    access_token: str = "test_access_token",
    refresh_token: str = "test_refresh_token",
) -> StreamingConnection:
    if token_expires_at is None:
        token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    conn = StreamingConnection(
        church_id=church_id,
        platform="youtube",
        access_token_encrypted=encrypt(access_token),
        refresh_token_encrypted=encrypt(refresh_token),
        token_expires_at=token_expires_at,
        external_user_id="UC_test_channel_id",
        status="active",
    )
    db.add(conn)
    await db.flush()
    return conn


@pytest_asyncio.fixture
async def church_id(db: AsyncSession) -> uuid.UUID:
    from app.models.church import Church

    unique_slug = f"test-yt-church-{uuid.uuid4().hex[:8]}"
    church = Church(name="Test YouTube Church", slug=unique_slug)
    db.add(church)
    await db.flush()
    return church.id


# ---------------------------------------------------------------------------
# search_tracks: happy path + cache behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_tracks_success_writes_cache(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = YouTubeAdapter(conn, db)

    with patch("app.adapters.youtube_adapter.YTMusic.search", return_value=FAKE_YTM_RESULTS):
        results = await adapter.search_tracks("How Great Is Our God")

    assert len(results) == 2
    first = results[0]
    assert first.track_id == "abc123XYZ01"
    assert first.title == "How Great Is Our God"
    assert first.artist == "Chris Tomlin"
    assert first.album == "Arriving"
    assert first.image_url == "https://lh3.googleusercontent.com/thumb_large.jpg"
    assert first.duration_ms is None

    # Cache row should exist
    cached_row = (
        await db.execute(
            select(SearchCache).where(
                SearchCache.platform == "youtube",
                SearchCache.query == "How Great Is Our God",
            )
        )
    ).scalar_one()
    assert cached_row is not None
    assert len(cached_row.results["items"]) == 2


@pytest.mark.asyncio
async def test_search_tracks_uses_fresh_cache(db: AsyncSession, church_id: uuid.UUID):
    """When cache is fresh (<7 days), ytmusicapi should not be called."""
    conn = await make_streaming_connection(db, church_id)
    adapter = YouTubeAdapter(conn, db)

    db.add(
        SearchCache(
            platform="youtube",
            query="cached query",
            results={
                "items": [
                    {
                        "track_id": "cached_video_id",
                        "title": "Cached Title",
                        "artist": "Cached Artist",
                        "album": None,
                        "image_url": None,
                        "duration_ms": None,
                    }
                ]
            },
        )
    )
    await db.flush()

    with patch("app.adapters.youtube_adapter.YTMusic.search") as mock_search:
        results = await adapter.search_tracks("cached query")
        mock_search.assert_not_called()

    assert len(results) == 1
    assert results[0].track_id == "cached_video_id"
    assert results[0].title == "Cached Title"


@pytest.mark.asyncio
async def test_search_tracks_ignores_stale_cache(db: AsyncSession, church_id: uuid.UUID):
    """When cache is older than 7 days, ytmusicapi should be called and cache refreshed."""
    conn = await make_streaming_connection(db, church_id)
    adapter = YouTubeAdapter(conn, db)

    stale_created_at = datetime.now(timezone.utc) - timedelta(days=8)
    db.add(
        SearchCache(
            platform="youtube",
            query="stale query",
            results={
                "items": [
                    {
                        "track_id": "old_video_id",
                        "title": "Old Title",
                        "artist": "Old Artist",
                        "album": None,
                        "image_url": None,
                        "duration_ms": None,
                    }
                ]
            },
            created_at=stale_created_at,
        )
    )
    await db.flush()

    with patch("app.adapters.youtube_adapter.YTMusic.search", return_value=FAKE_YTM_RESULTS) as mock_search:
        results = await adapter.search_tracks("stale query")
        mock_search.assert_called_once()

    # Fresh results returned (not the stale cached ones)
    assert results[0].track_id == "abc123XYZ01"

    # Cache row should have been updated
    refreshed = (
        await db.execute(
            select(SearchCache).where(
                SearchCache.platform == "youtube",
                SearchCache.query == "stale query",
            )
        )
    ).scalar_one()
    assert refreshed.results["items"][0]["track_id"] == "abc123XYZ01"


# ---------------------------------------------------------------------------
# create_playlist
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_create_playlist_returns_music_url(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = YouTubeAdapter(conn, db)

    respx.post("https://www.googleapis.com/youtube/v3/playlists").mock(
        return_value=Response(200, json=YOUTUBE_CREATE_PLAYLIST_RESPONSE)
    )

    playlist = await adapter.create_playlist(
        name="Sunday Morning Worship",
        description="Songs for this week",
    )

    assert playlist.external_id == "PL_ytplaylist123"
    assert playlist.url == "https://music.youtube.com/playlist?list=PL_ytplaylist123"
    assert playlist.name == "Sunday Morning Worship"


# ---------------------------------------------------------------------------
# replace_playlist_tracks: diff behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_replace_playlist_tracks_noop_when_identical(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = YouTubeAdapter(conn, db)

    list_route = respx.get("https://www.googleapis.com/youtube/v3/playlistItems").mock(
        return_value=Response(200, json=YOUTUBE_PLAYLIST_ITEMS_RESPONSE)
    )
    delete_route = respx.delete("https://www.googleapis.com/youtube/v3/playlistItems")
    insert_route = respx.post("https://www.googleapis.com/youtube/v3/playlistItems")

    await adapter.replace_playlist_tracks(
        "PL_ytplaylist123",
        ["abc123XYZ01", "def456UVW02"],
    )

    assert list_route.called
    assert not delete_route.called
    assert not insert_route.called


@pytest.mark.asyncio
@respx.mock
async def test_replace_playlist_tracks_deletes_and_inserts_when_differs(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = YouTubeAdapter(conn, db)

    respx.get("https://www.googleapis.com/youtube/v3/playlistItems").mock(
        return_value=Response(200, json=YOUTUBE_PLAYLIST_ITEMS_RESPONSE)
    )
    delete_route = respx.delete("https://www.googleapis.com/youtube/v3/playlistItems").mock(return_value=Response(204))
    insert_route = respx.post("https://www.googleapis.com/youtube/v3/playlistItems").mock(
        return_value=Response(200, json={"id": "new_item"})
    )

    await adapter.replace_playlist_tracks(
        "PL_ytplaylist123",
        ["newvid1", "newvid2", "newvid3"],
    )

    # Two existing items -> two deletes
    assert delete_route.call_count == 2
    # Three target video ids -> three inserts
    assert insert_route.call_count == 3


# ---------------------------------------------------------------------------
# validate_connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_validate_connection_success(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = YouTubeAdapter(conn, db)

    respx.get("https://www.googleapis.com/youtube/v3/channels").mock(
        return_value=Response(200, json={"items": [{"id": "UC_test_channel_id"}]})
    )

    assert await adapter.validate_connection() is True


@pytest.mark.asyncio
@respx.mock
async def test_validate_connection_401_returns_false(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = YouTubeAdapter(conn, db)

    respx.get("https://www.googleapis.com/youtube/v3/channels").mock(
        return_value=Response(401, json={"error": "Unauthorized"})
    )

    assert await adapter.validate_connection() is False
    assert conn.status == "error"


# ---------------------------------------------------------------------------
# get_playlist_url (no API call)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_playlist_url_is_music_youtube(db: AsyncSession, church_id: uuid.UUID):
    conn = await make_streaming_connection(db, church_id)
    adapter = YouTubeAdapter(conn, db)

    url = await adapter.get_playlist_url("PL_ytplaylist123")
    assert url == "https://music.youtube.com/playlist?list=PL_ytplaylist123"


# ---------------------------------------------------------------------------
# refresh_youtube_token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_refresh_youtube_token_updates_connection(db: AsyncSession, church_id: uuid.UUID):
    soon_expiry = datetime.now(timezone.utc) + timedelta(minutes=1)
    conn = await make_streaming_connection(
        db,
        church_id,
        token_expires_at=soon_expiry,
        refresh_token="original_refresh_token",
    )

    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=Response(
            200,
            json={
                "access_token": "new_yt_access_token",
                "expires_in": 3600,
                "scope": "https://www.googleapis.com/auth/youtube",
                "token_type": "Bearer",
            },
        )
    )

    new_token = await refresh_youtube_token(db, conn)

    assert new_token == "new_yt_access_token"
    assert decrypt(conn.access_token_encrypted) == "new_yt_access_token"
    # Google omitted refresh_token -> original must be preserved
    assert decrypt(conn.refresh_token_encrypted) == "original_refresh_token"
    assert conn.token_expires_at > soon_expiry
    assert conn.status == "active"
