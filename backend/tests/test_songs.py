"""Song matching endpoint integration tests — Epic 6.

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
from app.models.search_cache import SearchCache
from app.models.song_mapping import SongMapping
from app.models.streaming_connection import StreamingConnection
from app.utils.encryption import encrypt
from tests.fixtures.pco_responses import (
    PLAN_ITEMS_WITH_SONGS_RESPONSE,
    UPCOMING_PLANS_RESPONSE,
)
from tests.fixtures.spotify_responses import SPOTIFY_SEARCH_RESPONSE

PCO_BASE = "https://api.planningcenteronline.com"
SPOTIFY_BASE = "https://api.spotify.com/v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def get_verified_church_id(db: AsyncSession) -> uuid.UUID:
    """Return the church_id of the verified test user."""
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = result.scalar_one()
    return user.church_id


async def setup_church_connections(db: AsyncSession, church_id: uuid.UUID) -> None:
    """Add PCO connection and active Spotify streaming connection for a church."""
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
    await db.flush()


# ---------------------------------------------------------------------------
# Test 1: GET /api/songs/unmatched — returns only unmatched songs
# ---------------------------------------------------------------------------


@respx.mock
async def test_unmatched_songs_returns_unmatched_only(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)
    await setup_church_connections(db, church_id)

    # Mock PCO upcoming plans (2 plans)
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans").mock(
        return_value=Response(200, json=UPCOMING_PLANS_RESPONSE)
    )
    # Mock plan songs for plan 1001
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    # Mock plan songs for plan 1002 (same songs for simplicity)
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1002/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )

    # Pre-insert a mapping for song-1 ("How Great Is Our God")
    mapping = SongMapping(
        church_id=church_id,
        pco_song_id="song-1",
        pco_song_title="How Great Is Our God",
        pco_song_artist="Chris Tomlin",
        platform="spotify",
        track_id="spotify:track:abc",
        track_title="How Great Is Our God",
        track_artist="Chris Tomlin",
    )
    db.add(mapping)
    await db.flush()

    response = await verified_authenticated_client.get("/api/songs/unmatched?platform=spotify")

    assert response.status_code == 200
    body = response.json()
    song_ids = [s["pco_song_id"] for s in body["unmatched_songs"]]
    assert "song-2" in song_ids
    assert "song-1" not in song_ids


# ---------------------------------------------------------------------------
# Test 2: GET /api/songs/unmatched — empty when all songs matched
# ---------------------------------------------------------------------------


@respx.mock
async def test_unmatched_songs_empty_when_all_matched(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)
    await setup_church_connections(db, church_id)

    # Mock PCO: 1 plan with 2 songs
    single_plan_response = {"data": [UPCOMING_PLANS_RESPONSE["data"][0]]}
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans").mock(
        return_value=Response(200, json=single_plan_response)
    )
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )

    # Map both songs
    for song_id, title, artist in [
        ("song-1", "How Great Is Our God", "Chris Tomlin"),
        ("song-2", "Amazing Grace", "John Newton"),
    ]:
        db.add(
            SongMapping(
                church_id=church_id,
                pco_song_id=song_id,
                pco_song_title=title,
                pco_song_artist=artist,
                platform="spotify",
                track_id=f"spotify:track:{song_id}",
                track_title=title,
                track_artist=artist,
            )
        )
    await db.flush()

    response = await verified_authenticated_client.get("/api/songs/unmatched?platform=spotify")

    assert response.status_code == 200
    assert response.json()["unmatched_songs"] == []


# ---------------------------------------------------------------------------
# Test 3: GET /api/songs/unmatched — 400 when PCO not connected
# ---------------------------------------------------------------------------


async def test_unmatched_songs_no_pco_connection(verified_authenticated_client: AsyncClient):
    response = await verified_authenticated_client.get("/api/songs/unmatched?platform=spotify")

    assert response.status_code == 400
    assert response.json()["detail"] == "pco_not_connected"


# ---------------------------------------------------------------------------
# Test 4: GET /api/songs/search — cache miss calls Spotify
# ---------------------------------------------------------------------------


@respx.mock
async def test_search_cache_miss_calls_spotify(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)
    await setup_church_connections(db, church_id)

    respx.get(f"{SPOTIFY_BASE}/search").mock(return_value=Response(200, json=SPOTIFY_SEARCH_RESPONSE))

    response = await verified_authenticated_client.get("/api/songs/search?platform=spotify&q=How+Great")

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2

    # Verify cache row was created with normalized query
    cache_result = await db.execute(
        select(SearchCache).where(
            SearchCache.platform == "spotify",
            SearchCache.query == "how great",
        )
    )
    cached = cache_result.scalar_one_or_none()
    assert cached is not None
    assert len(cached.results) == 2


# ---------------------------------------------------------------------------
# Test 5: GET /api/songs/search — cache hit does not call Spotify
# ---------------------------------------------------------------------------


async def test_search_cache_hit_does_not_call_spotify(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)
    await setup_church_connections(db, church_id)

    # Pre-insert a fresh cache row
    cached_results = [
        {
            "track_id": "spotify:track:cached1",
            "title": "Cached Song",
            "artist": "Cached Artist",
            "album": "Cached Album",
            "image_url": None,
            "duration_ms": 180000,
        }
    ]
    cache_row = SearchCache(
        platform="spotify",
        query="how great",
        results=cached_results,
    )
    db.add(cache_row)
    await db.flush()

    # No respx mock — if Spotify is called, respx will raise an error
    response = await verified_authenticated_client.get("/api/songs/search?platform=spotify&q=How+Great")

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["track_id"] == "spotify:track:cached1"


# ---------------------------------------------------------------------------
# Test 6: GET /api/songs/search — stale cache is refreshed
# ---------------------------------------------------------------------------


@respx.mock
async def test_search_stale_cache_refreshed(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)
    await setup_church_connections(db, church_id)

    # Pre-insert a stale cache row (8 days old)
    stale_results = [
        {
            "track_id": "spotify:track:stale",
            "title": "Stale Song",
            "artist": "Stale Artist",
            "album": None,
            "image_url": None,
            "duration_ms": None,
        }
    ]
    stale_created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=8)
    cache_row = SearchCache(
        platform="spotify",
        query="how great",
        results=stale_results,
        created_at=stale_created_at,
    )
    db.add(cache_row)
    await db.flush()

    respx.get(f"{SPOTIFY_BASE}/search").mock(return_value=Response(200, json=SPOTIFY_SEARCH_RESPONSE))

    response = await verified_authenticated_client.get("/api/songs/search?platform=spotify&q=How+Great")

    assert response.status_code == 200
    body = response.json()
    # Should return fresh Spotify results, not stale ones
    assert len(body["results"]) == 2
    track_ids = [r["track_id"] for r in body["results"]]
    assert "spotify:track:stale" not in track_ids

    # Verify the cache row was updated
    await db.refresh(cache_row)
    assert len(cache_row.results) == 2
    assert cache_row.created_at > stale_created_at


# ---------------------------------------------------------------------------
# Test 7: GET /api/songs/search — 400 when no streaming connection
# ---------------------------------------------------------------------------


async def test_search_no_streaming_connection(verified_authenticated_client: AsyncClient):
    response = await verified_authenticated_client.get("/api/songs/search?platform=spotify&q=test")

    assert response.status_code == 400
    assert response.json()["detail"] == "streaming_not_connected"


# ---------------------------------------------------------------------------
# Test 8: POST /api/songs/match — creates a new mapping
# ---------------------------------------------------------------------------


async def test_match_creates_mapping(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)

    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    response = await verified_authenticated_client.post(
        "/api/songs/match",
        json={
            "pco_song_id": "song-1",
            "pco_song_title": "How Great Is Our God",
            "pco_song_artist": "Chris Tomlin",
            "platform": "spotify",
            "track_id": "spotify:track:abc",
            "track_title": "How Great Is Our God",
            "track_artist": "Chris Tomlin",
        },
        headers={"x-csrf-token": csrf},
    )

    assert response.status_code == 201
    body = response.json()
    assert "mapping_id" in body
    assert body["pco_song_title"] == "How Great Is Our God"
    assert body["track_title"] == "How Great Is Our God"
    assert body["platform"] == "spotify"

    # Verify DB row exists with correct fields
    result = await db.execute(
        select(SongMapping).where(
            SongMapping.church_id == church_id,
            SongMapping.pco_song_id == "song-1",
            SongMapping.platform == "spotify",
        )
    )
    mapping = result.scalar_one()
    assert str(mapping.track_id) == "spotify:track:abc"
    assert mapping.matched_by_user_id is not None


# ---------------------------------------------------------------------------
# Test 9: POST /api/songs/match — upsert updates existing mapping
# ---------------------------------------------------------------------------


async def test_match_upsert_updates_existing(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)

    # Insert an existing mapping with old track
    existing = SongMapping(
        church_id=church_id,
        pco_song_id="song-1",
        pco_song_title="How Great Is Our God",
        pco_song_artist="Chris Tomlin",
        platform="spotify",
        track_id="old-track",
        track_title="Old Track Title",
        track_artist="Old Artist",
    )
    db.add(existing)
    await db.flush()

    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    response = await verified_authenticated_client.post(
        "/api/songs/match",
        json={
            "pco_song_id": "song-1",
            "pco_song_title": "How Great Is Our God",
            "pco_song_artist": "Chris Tomlin",
            "platform": "spotify",
            "track_id": "new-track",
            "track_title": "New Track Title",
            "track_artist": "New Artist",
        },
        headers={"x-csrf-token": csrf},
    )

    assert response.status_code == 201
    assert response.json()["track_title"] == "New Track Title"

    # Verify exactly 1 row and it has the new track_id
    result = await db.execute(
        select(SongMapping).where(
            SongMapping.church_id == church_id,
            SongMapping.pco_song_id == "song-1",
            SongMapping.platform == "spotify",
        )
    )
    all_mappings = result.scalars().all()
    assert len(all_mappings) == 1
    assert all_mappings[0].track_id == "new-track"


# ---------------------------------------------------------------------------
# Test 10: GET /api/songs/mappings — returns all mappings
# ---------------------------------------------------------------------------


async def test_list_mappings(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)

    for song_id, title in [("song-1", "Song One"), ("song-2", "Song Two")]:
        db.add(
            SongMapping(
                church_id=church_id,
                pco_song_id=song_id,
                pco_song_title=title,
                platform="spotify",
                track_id=f"spotify:track:{song_id}",
                track_title=title,
            )
        )
    await db.flush()

    response = await verified_authenticated_client.get("/api/songs/mappings")

    assert response.status_code == 200
    body = response.json()
    assert len(body["mappings"]) == 2


# ---------------------------------------------------------------------------
# Test 11: GET /api/songs/mappings — filtered by platform
# ---------------------------------------------------------------------------


async def test_list_mappings_filtered_by_platform(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)

    db.add(
        SongMapping(
            church_id=church_id,
            pco_song_id="song-1",
            pco_song_title="Song One",
            platform="spotify",
            track_id="spotify:track:song1",
            track_title="Song One",
        )
    )
    db.add(
        SongMapping(
            church_id=church_id,
            pco_song_id="song-2",
            pco_song_title="Song Two",
            platform="youtube",
            track_id="youtube:video:song2",
            track_title="Song Two",
        )
    )
    await db.flush()

    response = await verified_authenticated_client.get("/api/songs/mappings?platform=spotify")

    assert response.status_code == 200
    body = response.json()
    assert len(body["mappings"]) == 1
    assert body["mappings"][0]["platform"] == "spotify"


# ---------------------------------------------------------------------------
# Test 12: DELETE /api/songs/mappings/{mapping_id} — success
# ---------------------------------------------------------------------------


async def test_delete_mapping_success(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)

    mapping = SongMapping(
        church_id=church_id,
        pco_song_id="song-1",
        pco_song_title="Song One",
        platform="spotify",
        track_id="spotify:track:abc",
        track_title="Song One",
    )
    db.add(mapping)
    await db.flush()
    mapping_id = mapping.id

    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    response = await verified_authenticated_client.delete(
        f"/api/songs/mappings/{mapping_id}",
        headers={"x-csrf-token": csrf},
    )

    assert response.status_code == 204

    # Verify row is deleted
    result = await db.execute(select(SongMapping).where(SongMapping.id == mapping_id))
    assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# Test 13: DELETE /api/songs/mappings/{mapping_id} — not found
# ---------------------------------------------------------------------------


async def test_delete_mapping_not_found(verified_authenticated_client: AsyncClient):
    random_id = uuid.uuid4()
    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    response = await verified_authenticated_client.delete(
        f"/api/songs/mappings/{random_id}",
        headers={"x-csrf-token": csrf},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test 14: DELETE /api/songs/mappings/{mapping_id} — tenant isolation
# ---------------------------------------------------------------------------


async def test_delete_mapping_tenant_isolation(verified_authenticated_client: AsyncClient, db: AsyncSession):
    # Create a second church and mapping
    other_church = Church(name="Other Church", slug="other-church")
    db.add(other_church)
    await db.flush()

    other_mapping = SongMapping(
        church_id=other_church.id,
        pco_song_id="song-x",
        pco_song_title="Other Song",
        platform="spotify",
        track_id="spotify:track:other",
        track_title="Other Song",
    )
    db.add(other_mapping)
    await db.flush()
    other_mapping_id = other_mapping.id

    csrf = verified_authenticated_client.cookies.get("csrf_token", "")
    response = await verified_authenticated_client.delete(
        f"/api/songs/mappings/{other_mapping_id}",
        headers={"x-csrf-token": csrf},
    )

    assert response.status_code == 404

    # Verify the mapping still exists
    result = await db.execute(select(SongMapping).where(SongMapping.id == other_mapping_id))
    assert result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Test 15: GET /api/songs/mappings — tenant isolation
# ---------------------------------------------------------------------------


async def test_list_mappings_tenant_isolation(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)

    # Church A mapping
    db.add(
        SongMapping(
            church_id=church_id,
            pco_song_id="song-a",
            pco_song_title="Church A Song",
            platform="spotify",
            track_id="spotify:track:a",
            track_title="Church A Song",
        )
    )

    # Church B mapping
    other_church = Church(name="Other Church B", slug="other-church-b")
    db.add(other_church)
    await db.flush()

    db.add(
        SongMapping(
            church_id=other_church.id,
            pco_song_id="song-b",
            pco_song_title="Church B Song",
            platform="spotify",
            track_id="spotify:track:b",
            track_title="Church B Song",
        )
    )
    await db.flush()

    response = await verified_authenticated_client.get("/api/songs/mappings")

    assert response.status_code == 200
    body = response.json()
    assert len(body["mappings"]) == 1
    assert body["mappings"][0]["pco_song_id"] == "song-a"


# ---------------------------------------------------------------------------
# Test 16: Endpoints require verified email
# ---------------------------------------------------------------------------


async def test_endpoints_require_verified_email(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/songs/unmatched?platform=spotify")

    assert response.status_code == 403
    assert response.json()["detail"] == "email_not_verified"


# ---------------------------------------------------------------------------
# Test 17: Endpoints require authentication
# ---------------------------------------------------------------------------


async def test_endpoints_require_authentication(client: AsyncClient):
    # GET /api/health to obtain a CSRF cookie
    await client.get("/api/health")

    response = await client.get("/api/songs/unmatched?platform=spotify")

    assert response.status_code == 401
