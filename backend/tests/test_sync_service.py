"""Sync service integration tests — Epic 7.

Tests use real PostgreSQL (service_tracks_test DB) with per-test transaction rollback.
Outbound PCO and Spotify HTTP calls are mocked via respx.
asyncio_mode = "auto" (set in pyproject.toml) makes all async test functions run automatically.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import respx
from httpx import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.church import Church
from app.models.church_user import ChurchUser
from app.models.pco_connection import PcoConnection
from app.models.playlist import Playlist
from app.models.song_mapping import SongMapping
from app.models.streaming_connection import StreamingConnection
from app.models.sync_log import SyncLog
from app.services.sync_service import sync_church, sync_plan
from app.utils.encryption import encrypt
from tests.fixtures.pco_responses import (
    PLAN_ITEMS_WITH_SONGS_RESPONSE,
    UPCOMING_PLANS_RESPONSE,
)
from tests.fixtures.spotify_responses import (
    SPOTIFY_CREATE_PLAYLIST_RESPONSE,
    SPOTIFY_REPLACE_TRACKS_RESPONSE,
)

PCO_BASE = "https://api.planningcenteronline.com"
SPOTIFY_BASE = "https://api.spotify.com/v1"

# Standard PCO plan metadata response (used when sync_plan auto-fetches plan_date)
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
    """Return the church_id of the verified test user."""
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = result.scalar_one()
    return user.church_id


async def setup_full_church(db: AsyncSession, church_id: uuid.UUID) -> None:
    """Set up a church with PCO connection, Spotify connection, and pco_service_type_id."""
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


async def add_song_mapping(
    db: AsyncSession,
    church_id: uuid.UUID,
    pco_song_id: str,
    title: str,
    track_id: str,
) -> None:
    """Helper to add a single song mapping."""
    db.add(
        SongMapping(
            church_id=church_id,
            pco_song_id=pco_song_id,
            pco_song_title=title,
            platform="spotify",
            track_id=track_id,
            track_title=title,
        )
    )
    await db.flush()


# ---------------------------------------------------------------------------
# Test 1: Happy path — all songs matched
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_plan_happy_path(db: AsyncSession, verified_authenticated_client):
    church_id = await get_verified_church_id(db)
    await setup_full_church(db, church_id)

    # Add mappings for both songs
    await add_song_mapping(db, church_id, "song-1", "How Great Is Our God", "spotify:track:track1")
    await add_song_mapping(db, church_id, "song-2", "Amazing Grace", "spotify:track:track2")

    # Mock PCO plan songs
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    # No existing playlist by this name on Spotify
    respx.get(f"{SPOTIFY_BASE}/me/playlists").mock(
        return_value=Response(200, json={"items": [], "total": 0})
    )
    # Mock Spotify create playlist
    respx.post(f"{SPOTIFY_BASE}/users/spotify_user_123/playlists").mock(
        return_value=Response(201, json=SPOTIFY_CREATE_PLAYLIST_RESPONSE)
    )
    # Mock Spotify replace tracks
    respx.put(f"{SPOTIFY_BASE}/playlists/playlist123/tracks").mock(
        return_value=Response(201, json=SPOTIFY_REPLACE_TRACKS_RESPONSE)
    )

    result = await sync_plan(
        db, church_id, "1001", "manual", plan_date=date(2026, 3, 22), plan_title="Sunday Service"
    )

    assert result.sync_status == "synced"
    assert result.songs_total == 2
    assert result.songs_matched == 2
    assert result.songs_unmatched == 0
    assert len(result.platforms) == 1
    assert result.platforms[0].sync_status == "synced"

    # Check playlist row created with synced status (shared mode uses "__shared__" as plan id)
    playlist_result = await db.execute(
        select(Playlist).where(
            Playlist.church_id == church_id,
            Playlist.pco_plan_id == "__shared__",
            Playlist.platform == "spotify",
        )
    )
    playlist = playlist_result.scalar_one()
    assert playlist.sync_status == "synced"
    assert playlist.external_playlist_id == "playlist123"
    assert playlist.last_known_track_ids == ["spotify:track:track1", "spotify:track:track2"]
    assert playlist.last_synced_at is not None

    # Check SyncLog row created
    log_result = await db.execute(
        select(SyncLog).where(
            SyncLog.church_id == church_id,
            SyncLog.sync_trigger == "manual",
        )
    )
    sync_log = log_result.scalar_one()
    assert sync_log.songs_total == 2
    assert sync_log.songs_matched == 2
    assert sync_log.status == "synced"


# ---------------------------------------------------------------------------
# Test 2: Partial match — some songs matched, some not
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_plan_partial_match(db: AsyncSession, verified_authenticated_client):
    church_id = await get_verified_church_id(db)
    await setup_full_church(db, church_id)

    # Only map song-1, not song-2
    await add_song_mapping(db, church_id, "song-1", "How Great Is Our God", "spotify:track:track1")

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

    result = await sync_plan(db, church_id, "1001", "manual", plan_date=date(2026, 3, 22))

    assert result.sync_status == "synced"
    assert result.songs_total == 2
    assert result.songs_matched == 1
    assert result.songs_unmatched == 1

    # Playlist synced with only the matched track (shared mode uses "__shared__" as plan id)
    playlist_result = await db.execute(
        select(Playlist).where(
            Playlist.church_id == church_id,
            Playlist.pco_plan_id == "__shared__",
        )
    )
    playlist = playlist_result.scalar_one()
    assert playlist.sync_status == "synced"
    assert playlist.last_known_track_ids == ["spotify:track:track1"]

    log_result = await db.execute(select(SyncLog).where(SyncLog.church_id == church_id))
    sync_log = log_result.scalar_one()
    assert sync_log.songs_unmatched == 1


# ---------------------------------------------------------------------------
# Test 3: No matches — all songs unmatched
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_plan_no_matches(db: AsyncSession, verified_authenticated_client):
    church_id = await get_verified_church_id(db)
    await setup_full_church(db, church_id)

    # No song mappings
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    # No existing playlist by this name on Spotify
    respx.get(f"{SPOTIFY_BASE}/me/playlists").mock(
        return_value=Response(200, json={"items": [], "total": 0})
    )
    # Playlist still gets created even with no matched tracks
    respx.post(f"{SPOTIFY_BASE}/users/spotify_user_123/playlists").mock(
        return_value=Response(201, json=SPOTIFY_CREATE_PLAYLIST_RESPONSE)
    )
    # Do NOT mock PUT /tracks — should NOT be called

    result = await sync_plan(db, church_id, "1001", "manual", plan_date=date(2026, 3, 22))

    assert result.sync_status == "pending"
    assert result.songs_matched == 0
    assert result.songs_unmatched == 2

    playlist_result = await db.execute(
        select(Playlist).where(
            Playlist.church_id == church_id,
            Playlist.pco_plan_id == "__shared__",
        )
    )
    playlist = playlist_result.scalar_one()
    assert playlist.sync_status == "pending"


# ---------------------------------------------------------------------------
# Test 4: Existing playlist — skip create, use existing
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_plan_existing_playlist(db: AsyncSession, verified_authenticated_client):
    church_id = await get_verified_church_id(db)
    await setup_full_church(db, church_id)
    await add_song_mapping(db, church_id, "song-1", "How Great Is Our God", "spotify:track:track1")

    # Pre-insert a Playlist row using "__shared__" sentinel (shared mode default)
    existing_playlist = Playlist(
        church_id=church_id,
        pco_plan_id="__shared__",
        pco_plan_date=date(2026, 3, 22),
        platform="spotify",
        external_playlist_id="existing_pl",
        external_playlist_url="https://open.spotify.com/playlist/existing_pl",
        sync_status="pending",
    )
    db.add(existing_playlist)
    await db.flush()

    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    # Do NOT mock POST create playlist — should NOT be called
    # Mock update_playlist_details (shared mode calls PUT /playlists/{id})
    respx.put(f"{SPOTIFY_BASE}/playlists/existing_pl").mock(
        return_value=Response(200, json={})
    )
    # Mock replace tracks on existing playlist
    respx.put(f"{SPOTIFY_BASE}/playlists/existing_pl/tracks").mock(
        return_value=Response(201, json=SPOTIFY_REPLACE_TRACKS_RESPONSE)
    )

    result = await sync_plan(db, church_id, "1001", "manual", plan_date=date(2026, 3, 22))

    assert result.sync_status == "synced"

    # Confirm no new playlist row was created
    playlist_count_result = await db.execute(
        select(Playlist).where(
            Playlist.church_id == church_id,
            Playlist.pco_plan_id == "__shared__",
        )
    )
    playlists = playlist_count_result.scalars().all()
    assert len(playlists) == 1
    assert playlists[0].external_playlist_id == "existing_pl"
    assert playlists[0].last_synced_at is not None
    assert playlists[0].last_known_track_ids == ["spotify:track:track1"]


# ---------------------------------------------------------------------------
# Test 5: PCO API failure
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_plan_pco_failure(db: AsyncSession, verified_authenticated_client):
    church_id = await get_verified_church_id(db)
    await setup_full_church(db, church_id)

    # Auto-fetch of plan metadata succeeds; songs fetch returns 500
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001").mock(
        return_value=Response(200, json=PCO_PLAN_RESPONSE)
    )
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(500, json={"error": "Internal Server Error"})
    )
    # Do NOT mock Spotify — should NOT be called

    result = await sync_plan(db, church_id, "1001", "manual")

    assert result.sync_status == "error"
    assert len(result.platforms) == 0

    log_result = await db.execute(select(SyncLog).where(SyncLog.church_id == church_id))
    sync_log = log_result.scalar_one()
    assert sync_log.status == "error"


# ---------------------------------------------------------------------------
# Test 6: Spotify replace_playlist_tracks failure
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_plan_streaming_failure(db: AsyncSession, verified_authenticated_client):
    church_id = await get_verified_church_id(db)
    await setup_full_church(db, church_id)
    await add_song_mapping(db, church_id, "song-1", "How Great Is Our God", "spotify:track:track1")

    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    respx.get(f"{SPOTIFY_BASE}/me/playlists").mock(
        return_value=Response(200, json={"items": [], "total": 0})
    )
    respx.post(f"{SPOTIFY_BASE}/users/spotify_user_123/playlists").mock(
        return_value=Response(201, json=SPOTIFY_CREATE_PLAYLIST_RESPONSE)
    )
    # Spotify replace tracks returns 500
    respx.put(f"{SPOTIFY_BASE}/playlists/playlist123/tracks").mock(
        return_value=Response(500, json={"error": "Internal Server Error"})
    )

    # Should NOT raise — error is caught and logged
    result = await sync_plan(db, church_id, "1001", "manual", plan_date=date(2026, 3, 22))

    assert result.sync_status == "error"
    assert result.platforms[0].sync_status == "error"
    assert result.platforms[0].error_message is not None

    playlist_result = await db.execute(
        select(Playlist).where(
            Playlist.church_id == church_id,
            Playlist.pco_plan_id == "__shared__",
        )
    )
    playlist = playlist_result.scalar_one()
    assert playlist.sync_status == "error"
    assert playlist.error_message is not None

    log_result = await db.execute(select(SyncLog).where(SyncLog.church_id == church_id))
    sync_log = log_result.scalar_one()
    assert sync_log.status == "error"


# ---------------------------------------------------------------------------
# Test 7: No active streaming connections
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_plan_no_streaming_connections(db: AsyncSession, verified_authenticated_client):
    church_id = await get_verified_church_id(db)

    # Only PCO connection, no streaming connection
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
    await db.flush()

    # Do NOT mock any Spotify calls

    result = await sync_plan(db, church_id, "1001", "manual")

    assert result.sync_status == "skipped"
    assert result.platforms == []

    log_result = await db.execute(select(SyncLog).where(SyncLog.church_id == church_id))
    sync_log = log_result.scalar_one()
    assert sync_log.status == "skipped"


# ---------------------------------------------------------------------------
# Test 8: sync_church iterates all upcoming plans
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_church_calls_sync_plan_for_each_plan(db: AsyncSession, verified_authenticated_client):
    church_id = await get_verified_church_id(db)
    await setup_full_church(db, church_id)
    await add_song_mapping(db, church_id, "song-1", "How Great Is Our God", "spotify:track:track1")
    await add_song_mapping(db, church_id, "song-2", "Amazing Grace", "spotify:track:track2")

    # Mock PCO upcoming plans (returns 2 plans: 1001 and 1002)
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans").mock(
        return_value=Response(200, json=UPCOMING_PLANS_RESPONSE)
    )
    # Mock plan songs for plan 1001
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    # Mock plan songs for plan 1002
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1002/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )

    # In shared mode: plan 1001 creates the shared playlist, plan 1002 updates it in place.
    # Only 1 GET /me/playlists (for plan 1001 new-playlist check), 1 POST to create,
    # then 1 PUT to update_playlist_details, then 2 PUT to replace tracks.
    respx.get(f"{SPOTIFY_BASE}/me/playlists").mock(
        return_value=Response(200, json={"items": [], "total": 0})
    )
    create_playlist_response_shared = {
        "id": "playlist_shared",
        "name": "Verified Church Worship",
        "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist_shared"},
    }
    respx.post(f"{SPOTIFY_BASE}/users/spotify_user_123/playlists").mock(
        return_value=Response(201, json=create_playlist_response_shared)
    )
    # update_playlist_details called for plan 1002 (existing shared playlist)
    respx.put(f"{SPOTIFY_BASE}/playlists/playlist_shared").mock(
        return_value=Response(200, json={})
    )
    respx.put(f"{SPOTIFY_BASE}/playlists/playlist_shared/tracks").mock(
        return_value=Response(201, json=SPOTIFY_REPLACE_TRACKS_RESPONSE)
    )

    results = await sync_church(db, church_id)

    assert len(results) == 2
    assert all(r.sync_status == "synced" for r in results)

    # 2 SyncLog rows (one per plan)
    log_result = await db.execute(select(SyncLog).where(SyncLog.church_id == church_id))
    logs = log_result.scalars().all()
    assert len(logs) == 2

    # 1 Playlist row (shared mode reuses the same playlist for both plans)
    playlist_result = await db.execute(select(Playlist).where(Playlist.church_id == church_id))
    playlists = playlist_result.scalars().all()
    assert len(playlists) == 1
    assert playlists[0].pco_plan_id == "__shared__"


# ---------------------------------------------------------------------------
# Test 9: Shared mode — lookup uses "__shared__", update_playlist_details called on second sync
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_plan_shared_mode_second_sync_updates_details(
    db: AsyncSession, verified_authenticated_client
):
    """In shared mode, the second sync reuses the existing playlist and calls update_playlist_details."""
    church_id = await get_verified_church_id(db)
    await setup_full_church(db, church_id)
    await add_song_mapping(db, church_id, "song-1", "How Great Is Our God", "spotify:track:track1")

    # First sync: creates the shared playlist (find_playlist_by_name returns empty)
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

    result1 = await sync_plan(
        db, church_id, "1001", "manual", plan_date=date(2026, 3, 22), plan_title="Sunday Service"
    )
    assert result1.sync_status == "synced"

    # Verify shared playlist was created
    playlist_result = await db.execute(
        select(Playlist).where(
            Playlist.church_id == church_id,
            Playlist.pco_plan_id == "__shared__",
            Playlist.platform == "spotify",
        )
    )
    playlist = playlist_result.scalar_one()
    assert playlist.external_playlist_id == "playlist123"

    # Second sync for a different plan_id — should reuse shared playlist and call update_playlist_details
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1002/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    # update_playlist_details: PUT /playlists/{id} (no /tracks suffix)
    respx.put(f"{SPOTIFY_BASE}/playlists/playlist123").mock(
        return_value=Response(200, json={})
    )
    respx.put(f"{SPOTIFY_BASE}/playlists/playlist123/tracks").mock(
        return_value=Response(201, json=SPOTIFY_REPLACE_TRACKS_RESPONSE)
    )

    result2 = await sync_plan(
        db, church_id, "1002", "manual", plan_date=date(2026, 4, 5), plan_title="Easter Sunday"
    )
    assert result2.sync_status == "synced"

    # Still only 1 shared playlist row
    all_playlists_result = await db.execute(
        select(Playlist).where(Playlist.church_id == church_id)
    )
    all_playlists = all_playlists_result.scalars().all()
    assert len(all_playlists) == 1
    assert all_playlists[0].pco_plan_id == "__shared__"


# ---------------------------------------------------------------------------
# Test 10: Per-plan mode — lookup uses real plan_id, update_playlist_details not called
# ---------------------------------------------------------------------------


@respx.mock
async def test_sync_plan_per_plan_mode_uses_real_plan_id(
    db: AsyncSession, verified_authenticated_client
):
    """In per_plan mode, each plan gets its own playlist and update_playlist_details is not called."""
    church_id = await get_verified_church_id(db)
    await setup_full_church(db, church_id)
    await add_song_mapping(db, church_id, "song-1", "How Great Is Our God", "spotify:track:track1")

    # Set church to per_plan mode
    church_result = await db.execute(select(Church).where(Church.id == church_id))
    church = church_result.scalar_one()
    church.playlist_mode = "per_plan"
    await db.flush()

    # Sync plan 1001
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1001/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    create_1001 = {
        "id": "playlist_1001",
        "name": "Sunday Service - 2026-03-22",
        "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist_1001"},
    }
    respx.post(f"{SPOTIFY_BASE}/users/spotify_user_123/playlists").mock(
        return_value=Response(201, json=create_1001)
    )
    respx.put(f"{SPOTIFY_BASE}/playlists/playlist_1001/tracks").mock(
        return_value=Response(201, json=SPOTIFY_REPLACE_TRACKS_RESPONSE)
    )

    result = await sync_plan(
        db, church_id, "1001", "manual", plan_date=date(2026, 3, 22), plan_title="Sunday Service"
    )
    assert result.sync_status == "synced"

    # Verify playlist stored under real plan_id "1001" (not "__shared__")
    playlist_result = await db.execute(
        select(Playlist).where(
            Playlist.church_id == church_id,
            Playlist.pco_plan_id == "1001",
            Playlist.platform == "spotify",
        )
    )
    playlist = playlist_result.scalar_one()
    assert playlist.external_playlist_id == "playlist_1001"

    # Sync plan 1002 — should create a new separate playlist (no update_playlist_details call)
    respx.get(f"{PCO_BASE}/services/v2/service_types/111/plans/1002/items").mock(
        return_value=Response(200, json=PLAN_ITEMS_WITH_SONGS_RESPONSE)
    )
    create_1002 = {
        "id": "playlist_1002",
        "name": "Easter Sunday - 2026-04-05",
        "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist_1002"},
    }
    respx.post(f"{SPOTIFY_BASE}/users/spotify_user_123/playlists").mock(
        return_value=Response(201, json=create_1002)
    )
    respx.put(f"{SPOTIFY_BASE}/playlists/playlist_1002/tracks").mock(
        return_value=Response(201, json=SPOTIFY_REPLACE_TRACKS_RESPONSE)
    )
    # NOTE: Do NOT mock PUT /playlists/{id} (without /tracks) — update_playlist_details
    # should NOT be called in per_plan mode.

    result2 = await sync_plan(
        db, church_id, "1002", "manual", plan_date=date(2026, 4, 5), plan_title="Easter Sunday"
    )
    assert result2.sync_status == "synced"

    # 2 separate playlist rows
    all_playlists_result = await db.execute(
        select(Playlist).where(Playlist.church_id == church_id)
    )
    all_playlists = all_playlists_result.scalars().all()
    assert len(all_playlists) == 2
    plan_ids = {p.pco_plan_id for p in all_playlists}
    assert plan_ids == {"1001", "1002"}
