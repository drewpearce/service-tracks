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


async def setup_church_connections(
    db: AsyncSession,
    church_id: uuid.UUID,
    *,
    platforms: tuple[str, ...] = ("spotify",),
) -> None:
    """Add PCO connection and active streaming connections for the given platforms."""
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

    for platform in platforms:
        db.add(
            StreamingConnection(
                church_id=church_id,
                platform=platform,
                access_token_encrypted=encrypt("test_access_token"),
                refresh_token_encrypted=encrypt("test_refresh_token"),
                token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                external_user_id=f"{platform}_user_123",
                status="active",
            )
        )
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
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1002/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )

    # Pre-insert a mapping for song-1 ("How Great Is Our God") — fully matched on the
    # only connected platform (spotify), so song-1 should drop out of unmatched.
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

    response = await verified_authenticated_client.get("/api/songs/unmatched")

    assert response.status_code == 200
    body = response.json()
    song_ids = [s["pco_song_id"] for s in body["unmatched_songs"]]
    assert "song-2" in song_ids
    assert "song-1" not in song_ids
    # song-2 row carries per-platform state for every connected platform.
    song2 = next(s for s in body["unmatched_songs"] if s["pco_song_id"] == "song-2")
    assert song2["platforms"] == {
        "spotify": {
            "matched": False,
            "mapping_id": None,
            "track_id": None,
            "track_title": None,
            "track_artist": None,
        }
    }


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

    response = await verified_authenticated_client.get("/api/songs/unmatched")

    assert response.status_code == 200
    assert response.json()["unmatched_songs"] == []


# ---------------------------------------------------------------------------
# Test 3: GET /api/songs/unmatched — 400 when PCO not connected
# ---------------------------------------------------------------------------


async def test_unmatched_songs_no_pco_connection(verified_authenticated_client: AsyncClient):
    response = await verified_authenticated_client.get("/api/songs/unmatched")

    assert response.status_code == 400
    assert response.json()["detail"] == "pco_not_connected"


# ---------------------------------------------------------------------------
# Test 3b: GET /api/songs/unmatched — partial match across platforms
# ---------------------------------------------------------------------------


@respx.mock
async def test_unmatched_songs_partial_match_across_platforms(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """A song matched on Spotify but not YouTube still appears in Unmatched, with mixed state."""
    church_id = await get_verified_church_id(db)
    await setup_church_connections(db, church_id, platforms=("spotify", "youtube"))

    single_plan_response = {"data": [UPCOMING_PLANS_RESPONSE["data"][0]]}
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans").mock(
        return_value=Response(200, json=single_plan_response)
    )
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )

    # song-1 matched on Spotify only.
    db.add(
        SongMapping(
            church_id=church_id,
            pco_song_id="song-1",
            pco_song_title="How Great Is Our God",
            pco_song_artist="Chris Tomlin",
            platform="spotify",
            track_id="spotify:track:abc",
            track_title="How Great Is Our God",
            track_artist="Chris Tomlin",
        )
    )
    await db.flush()

    response = await verified_authenticated_client.get("/api/songs/unmatched")

    assert response.status_code == 200
    body = response.json()
    songs_by_id = {s["pco_song_id"]: s for s in body["unmatched_songs"]}
    # song-1 is only partially matched, so it stays in the unmatched list.
    assert "song-1" in songs_by_id
    song1_platforms = songs_by_id["song-1"]["platforms"]
    assert song1_platforms["spotify"]["matched"] is True
    assert song1_platforms["spotify"]["track_id"] == "spotify:track:abc"
    assert song1_platforms["spotify"]["mapping_id"] is not None
    assert song1_platforms["youtube"]["matched"] is False
    # song-2 has no mappings at all — both platforms unmatched.
    assert songs_by_id["song-2"]["platforms"]["spotify"]["matched"] is False
    assert songs_by_id["song-2"]["platforms"]["youtube"]["matched"] is False


# ---------------------------------------------------------------------------
# Test 3c: GET /api/songs/unmatched — fully matched on every connected platform drops out
# ---------------------------------------------------------------------------


@respx.mock
async def test_unmatched_songs_fully_matched_on_all_platforms(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    church_id = await get_verified_church_id(db)
    await setup_church_connections(db, church_id, platforms=("spotify", "youtube"))

    single_plan_response = {"data": [UPCOMING_PLANS_RESPONSE["data"][0]]}
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans").mock(
        return_value=Response(200, json=single_plan_response)
    )
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )

    for platform in ("spotify", "youtube"):
        db.add(
            SongMapping(
                church_id=church_id,
                pco_song_id="song-1",
                pco_song_title="How Great Is Our God",
                pco_song_artist="Chris Tomlin",
                platform=platform,
                track_id=f"{platform}:track:abc",
                track_title="How Great Is Our God",
                track_artist="Chris Tomlin",
            )
        )
    await db.flush()

    response = await verified_authenticated_client.get("/api/songs/unmatched")

    assert response.status_code == 200
    song_ids = [s["pco_song_id"] for s in response.json()["unmatched_songs"]]
    assert "song-1" not in song_ids
    assert "song-2" in song_ids


# ---------------------------------------------------------------------------
# Test 3d: GET /api/songs/unmatched — zero connected platforms returns empty
# ---------------------------------------------------------------------------


async def test_unmatched_songs_no_connected_platforms(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)
    await setup_church_connections(db, church_id, platforms=())

    response = await verified_authenticated_client.get("/api/songs/unmatched")

    assert response.status_code == 200
    assert response.json()["unmatched_songs"] == []


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

    # New fields propagate end-to-end (preview when Spotify returns one, null otherwise;
    # external_url always built from the bare track ID).
    first = body["results"][0]
    assert first["preview_url"] == "https://p.scdn.co/mp3-preview/abc123"
    assert first["external_url"] == "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"
    assert body["results"][1]["preview_url"] is None
    assert body["results"][1]["external_url"] == "https://open.spotify.com/track/7ouMYWpwJ422jRcDASZB7P"

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
    # Cache rows persist the new fields so subsequent hits don't lose them.
    assert cached.results[0]["preview_url"] == "https://p.scdn.co/mp3-preview/abc123"
    assert cached.results[0]["external_url"] == "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"


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
    # Legacy cache rows (pre-feature) lack the preview/external fields; schema defaults
    # surface them as null rather than failing validation.
    assert body["results"][0]["preview_url"] is None
    assert body["results"][0]["external_url"] is None


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
    assert cache_row.created_at.replace(tzinfo=None) > stale_created_at


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
    await setup_church_connections(db, church_id)

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
    assert len(body["songs"]) == 2
    for song in body["songs"]:
        assert song["platforms"]["spotify"]["matched"] is True


# ---------------------------------------------------------------------------
# Test 11: GET /api/songs/mappings — groups platforms per PCO song
# ---------------------------------------------------------------------------


async def test_list_mappings_groups_per_song(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """A song with mappings on both Spotify and YouTube collapses into a single row."""
    church_id = await get_verified_church_id(db)
    await setup_church_connections(db, church_id, platforms=("spotify", "youtube"))

    db.add(
        SongMapping(
            church_id=church_id,
            pco_song_id="song-1",
            pco_song_title="Song One",
            platform="spotify",
            track_id="spotify:track:song1",
            track_title="Song One (Spotify)",
        )
    )
    db.add(
        SongMapping(
            church_id=church_id,
            pco_song_id="song-1",
            pco_song_title="Song One",
            platform="youtube",
            track_id="youtube:video:song1",
            track_title="Song One (YouTube)",
        )
    )
    db.add(
        SongMapping(
            church_id=church_id,
            pco_song_id="song-2",
            pco_song_title="Song Two",
            platform="spotify",
            track_id="spotify:track:song2",
            track_title="Song Two",
        )
    )
    await db.flush()

    response = await verified_authenticated_client.get("/api/songs/mappings")

    assert response.status_code == 200
    body = response.json()
    songs_by_id = {s["pco_song_id"]: s for s in body["songs"]}

    assert len(body["songs"]) == 2
    assert songs_by_id["song-1"]["platforms"]["spotify"]["matched"] is True
    assert songs_by_id["song-1"]["platforms"]["spotify"]["track_title"] == "Song One (Spotify)"
    assert songs_by_id["song-1"]["platforms"]["youtube"]["matched"] is True
    assert songs_by_id["song-1"]["platforms"]["youtube"]["track_title"] == "Song One (YouTube)"
    # song-2 only has a Spotify mapping; YouTube row is unmatched.
    assert songs_by_id["song-2"]["platforms"]["spotify"]["matched"] is True
    assert songs_by_id["song-2"]["platforms"]["youtube"]["matched"] is False


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
    await setup_church_connections(db, church_id)

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
    assert len(body["songs"]) == 1
    assert body["songs"][0]["pco_song_id"] == "song-a"


# ---------------------------------------------------------------------------
# Test 16: GET /api/songs/{pco_song_id}/mappings — single-song mapping lookup
# ---------------------------------------------------------------------------


async def test_song_mappings_returns_state_per_connected_platform(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """A song matched on Spotify but not YouTube returns matched=True for Spotify, False for YouTube."""
    church_id = await get_verified_church_id(db)
    await setup_church_connections(db, church_id, platforms=("spotify", "youtube"))

    db.add(
        SongMapping(
            church_id=church_id,
            pco_song_id="song-1",
            pco_song_title="Hallelujah",
            pco_song_artist="Leonard Cohen",
            platform="spotify",
            track_id="spotify:track:abc",
            track_title="Hallelujah",
            track_artist="Leonard Cohen",
        )
    )
    await db.flush()

    response = await verified_authenticated_client.get("/api/songs/song-1/mappings")

    assert response.status_code == 200
    body = response.json()
    assert body["pco_song_id"] == "song-1"
    assert body["platforms"]["spotify"]["matched"] is True
    assert body["platforms"]["spotify"]["track_title"] == "Hallelujah"
    assert body["platforms"]["spotify"]["track_artist"] == "Leonard Cohen"
    assert body["platforms"]["youtube"]["matched"] is False


async def test_song_mappings_all_unmatched_when_no_rows(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """A song with no mappings still returns the connected-platform shape, all unmatched."""
    church_id = await get_verified_church_id(db)
    await setup_church_connections(db, church_id, platforms=("spotify", "youtube"))

    response = await verified_authenticated_client.get("/api/songs/unknown-song/mappings")

    assert response.status_code == 200
    body = response.json()
    assert body["pco_song_id"] == "unknown-song"
    assert body["platforms"]["spotify"]["matched"] is False
    assert body["platforms"]["youtube"]["matched"] is False


async def test_song_mappings_excludes_disconnected_platforms(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """Mappings on platforms the church no longer has connected are not returned."""
    church_id = await get_verified_church_id(db)
    # Only Spotify is connected.
    await setup_church_connections(db, church_id, platforms=("spotify",))

    db.add(
        SongMapping(
            church_id=church_id,
            pco_song_id="song-1",
            pco_song_title="Song One",
            platform="youtube",
            track_id="youtube:video:xyz",
            track_title="Song One",
        )
    )
    await db.flush()

    response = await verified_authenticated_client.get("/api/songs/song-1/mappings")

    assert response.status_code == 200
    body = response.json()
    assert "youtube" not in body["platforms"]
    assert body["platforms"]["spotify"]["matched"] is False


async def test_song_mappings_tenant_isolation(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """A mapping on another church for the same pco_song_id is not returned."""
    church_id = await get_verified_church_id(db)
    await setup_church_connections(db, church_id, platforms=("spotify",))

    other_church = Church(name="Other Church", slug="other-church-iso")
    db.add(other_church)
    await db.flush()

    db.add(
        SongMapping(
            church_id=other_church.id,
            pco_song_id="song-1",
            pco_song_title="Other Church Song",
            platform="spotify",
            track_id="spotify:track:other",
            track_title="Other Church Song",
        )
    )
    await db.flush()

    response = await verified_authenticated_client.get("/api/songs/song-1/mappings")

    assert response.status_code == 200
    body = response.json()
    assert body["platforms"]["spotify"]["matched"] is False


# ---------------------------------------------------------------------------
# Test 17: Endpoints require verified email
# ---------------------------------------------------------------------------


async def test_endpoints_require_verified_email(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/songs/unmatched")

    assert response.status_code == 403
    assert response.json()["detail"] == "email_not_verified"


# ---------------------------------------------------------------------------
# Test 17: Endpoints require authentication
# ---------------------------------------------------------------------------


async def test_endpoints_require_authentication(client: AsyncClient):
    # GET /api/health to obtain a CSRF cookie
    await client.get("/api/health")

    response = await client.get("/api/songs/unmatched")

    assert response.status_code == 401
