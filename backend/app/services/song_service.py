"""Song service layer — unmatched song detection, search with caching, and mapping CRUD."""

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.streaming import get_streaming_adapter
from app.models.pco_connection import PcoConnection
from app.models.search_cache import SearchCache
from app.models.song_mapping import SongMapping
from app.models.streaming_connection import StreamingConnection
from app.schemas.songs import (
    MatchRequest,
    TrackSearchResultSchema,
    UnmatchedSong,
)
from app.services import pco_service

logger = structlog.get_logger(__name__)


async def get_unmatched_songs(
    db: AsyncSession,
    church_id: uuid.UUID,
    platform: str,
) -> list[UnmatchedSong]:
    """Return songs from upcoming plans that don't have a mapping for the given platform.

    Raises:
        ValueError: "pco_not_connected" if no PCO connection exists.
        PcoApiError subclasses if the PCO API call fails.
    """
    # Check PCO connection exists before attempting to fetch plans
    conn_result = await db.execute(select(PcoConnection).where(PcoConnection.church_id == church_id))
    if conn_result.scalar_one_or_none() is None:
        raise ValueError("pco_not_connected")

    plans = await pco_service.get_upcoming_plans_for_church(db, church_id)
    if not plans:
        return []

    # Collect songs across all plans, keyed by pco_song_id.
    # Store earliest sort_date as last_used_date.
    songs_by_id: dict[str, UnmatchedSong] = {}

    for plan in plans:
        plan_songs = await pco_service.get_plan_songs_for_church(db, church_id, plan.id)
        for song in plan_songs:
            if song.pco_song_id not in songs_by_id:
                songs_by_id[song.pco_song_id] = UnmatchedSong(
                    pco_song_id=song.pco_song_id,
                    title=song.title,
                    artist=song.artist,
                    last_used_date=plan.sort_date,
                )
            else:
                # Keep the earliest date (plans are returned in date order, but be defensive)
                existing = songs_by_id[song.pco_song_id]
                if plan.sort_date < existing.last_used_date:
                    songs_by_id[song.pco_song_id] = UnmatchedSong(
                        pco_song_id=song.pco_song_id,
                        title=song.title,
                        artist=song.artist,
                        last_used_date=plan.sort_date,
                    )

    if not songs_by_id:
        return []

    # Query existing mappings for this church + platform
    mapping_result = await db.execute(
        select(SongMapping.pco_song_id).where(
            SongMapping.church_id == church_id,
            SongMapping.platform == platform,
        )
    )
    mapped_song_ids = {row[0] for row in mapping_result.all()}

    # Filter out songs that already have a mapping
    return [song for song in songs_by_id.values() if song.pco_song_id not in mapped_song_ids]


async def search_tracks(
    db: AsyncSession,
    church_id: uuid.UUID,
    platform: str,
    query: str,
) -> list[TrackSearchResultSchema]:
    """Search for tracks on the given platform, with a 7-day cache.

    Raises:
        ValueError: "streaming_not_connected" if no active connection exists.
        SpotifyApiError subclasses if the Spotify API call fails.
    """
    # Look up streaming connection
    conn_result = await db.execute(
        select(StreamingConnection).where(
            StreamingConnection.church_id == church_id,
            StreamingConnection.platform == platform,
            StreamingConnection.status == "active",
        )
    )
    connection = conn_result.scalar_one_or_none()
    if connection is None:
        raise ValueError("streaming_not_connected")

    # Normalize the query
    normalized = query.lower().strip()

    # Check cache (within last 7 days)
    cache_result = await db.execute(
        select(SearchCache).where(
            SearchCache.platform == platform,
            SearchCache.query == normalized,
            SearchCache.created_at > datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7),
        )
    )
    cached = cache_result.scalar_one_or_none()

    if cached is not None:
        # Cache hit — deserialize and return
        return [TrackSearchResultSchema(**item) for item in cached.results]

    # Cache miss — call the streaming adapter
    adapter = get_streaming_adapter(platform, connection, db=db)
    raw_results = await adapter.search_tracks(query)

    results_dicts = [
        {
            "track_id": r.track_id,
            "title": r.title,
            "artist": r.artist,
            "album": r.album,
            "image_url": r.image_url,
            "duration_ms": r.duration_ms,
        }
        for r in raw_results
    ]

    # Upsert into search_cache (handles stale entries via query-then-update)
    stale_result = await db.execute(
        select(SearchCache).where(
            SearchCache.platform == platform,
            SearchCache.query == normalized,
        )
    )
    stale_cache = stale_result.scalar_one_or_none()

    if stale_cache is not None:
        stale_cache.results = results_dicts
        stale_cache.created_at = datetime.now(timezone.utc)
    else:
        new_cache = SearchCache(
            platform=platform,
            query=normalized,
            results=results_dicts,
        )
        db.add(new_cache)

    await db.flush()

    return [TrackSearchResultSchema(**item) for item in results_dicts]


async def create_or_update_mapping(
    db: AsyncSession,
    church_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MatchRequest,
) -> SongMapping:
    """Upsert a song mapping for the given church/song/platform combination.

    If a mapping already exists for (church_id, pco_song_id, platform), update it.
    Otherwise, create a new mapping.
    """
    result = await db.execute(
        select(SongMapping).where(
            SongMapping.church_id == church_id,
            SongMapping.pco_song_id == data.pco_song_id,
            SongMapping.platform == data.platform,
        )
    )
    mapping = result.scalar_one_or_none()

    if mapping is not None:
        mapping.track_id = data.track_id
        mapping.track_title = data.track_title
        mapping.track_artist = data.track_artist
        mapping.pco_song_title = data.pco_song_title
        mapping.pco_song_artist = data.pco_song_artist
        mapping.matched_by_user_id = user_id
    else:
        mapping = SongMapping(
            church_id=church_id,
            pco_song_id=data.pco_song_id,
            pco_song_title=data.pco_song_title,
            pco_song_artist=data.pco_song_artist,
            platform=data.platform,
            track_id=data.track_id,
            track_title=data.track_title,
            track_artist=data.track_artist,
            matched_by_user_id=user_id,
        )
        db.add(mapping)

    await db.flush()
    return mapping


async def list_mappings(
    db: AsyncSession,
    church_id: uuid.UUID,
    platform: str | None,
) -> list[SongMapping]:
    """Return all song mappings for the given church, optionally filtered by platform."""
    query = select(SongMapping).where(SongMapping.church_id == church_id)
    if platform is not None:
        query = query.where(SongMapping.platform == platform)
    query = query.order_by(SongMapping.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_mapping(
    db: AsyncSession,
    church_id: uuid.UUID,
    mapping_id: uuid.UUID,
) -> bool:
    """Delete a song mapping, enforcing tenant isolation.

    Returns True if deleted, False if not found (or belongs to a different church).
    """
    result = await db.execute(
        select(SongMapping).where(
            SongMapping.id == mapping_id,
            SongMapping.church_id == church_id,
        )
    )
    mapping = result.scalar_one_or_none()

    if mapping is None:
        return False

    await db.delete(mapping)
    await db.flush()
    return True
