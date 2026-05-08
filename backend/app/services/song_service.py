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
    PlatformMappingState,
    SongWithPlatforms,
    TrackSearchResultSchema,
)
from app.services import pco_service

logger = structlog.get_logger(__name__)


async def _get_connected_platforms(db: AsyncSession, church_id: uuid.UUID) -> list[str]:
    """Return the list of streaming platforms with an active connection for the church."""
    result = await db.execute(
        select(StreamingConnection.platform).where(
            StreamingConnection.church_id == church_id,
            StreamingConnection.status == "active",
        )
    )
    return [row[0] for row in result.all()]


def _build_platform_state(
    connected_platforms: list[str],
    mappings_by_platform: dict[str, SongMapping],
) -> dict[str, PlatformMappingState]:
    """Build a per-platform mapping state map for one PCO song."""
    out: dict[str, PlatformMappingState] = {}
    for platform in connected_platforms:
        mapping = mappings_by_platform.get(platform)
        if mapping is not None:
            out[platform] = PlatformMappingState(
                matched=True,
                mapping_id=str(mapping.id),
                track_id=mapping.track_id,
                track_title=mapping.track_title,
                track_artist=mapping.track_artist,
            )
        else:
            out[platform] = PlatformMappingState(matched=False)
    return out


async def get_unmatched_songs(
    db: AsyncSession,
    church_id: uuid.UUID,
) -> list[SongWithPlatforms]:
    """Return upcoming-plan songs missing a match on at least one connected platform.

    Each returned song carries a per-platform state map keyed by every connected platform.

    Raises:
        ValueError: "pco_not_connected" if no PCO connection exists.
        PcoApiError subclasses if the PCO API call fails.
    """
    conn_result = await db.execute(select(PcoConnection).where(PcoConnection.church_id == church_id))
    if conn_result.scalar_one_or_none() is None:
        raise ValueError("pco_not_connected")

    connected_platforms = await _get_connected_platforms(db, church_id)
    if not connected_platforms:
        return []

    plans = await pco_service.get_upcoming_plans_for_church(db, church_id)
    if not plans:
        return []

    upcoming_songs: dict[str, dict[str, str | None]] = {}

    for plan in plans:
        plan_songs = await pco_service.get_plan_songs_for_church(db, church_id, plan.id)
        for song in plan_songs:
            existing = upcoming_songs.get(song.pco_song_id)
            if existing is None or plan.sort_date < existing["last_used_date"]:
                upcoming_songs[song.pco_song_id] = {
                    "title": song.title,
                    "artist": song.artist,
                    "last_used_date": plan.sort_date,
                }

    if not upcoming_songs:
        return []

    mapping_result = await db.execute(
        select(SongMapping).where(
            SongMapping.church_id == church_id,
            SongMapping.pco_song_id.in_(upcoming_songs.keys()),
        )
    )
    mappings_by_song: dict[str, dict[str, SongMapping]] = {}
    for mapping in mapping_result.scalars().all():
        mappings_by_song.setdefault(mapping.pco_song_id, {})[mapping.platform] = mapping

    out: list[SongWithPlatforms] = []
    for pco_song_id, info in upcoming_songs.items():
        platform_state = _build_platform_state(connected_platforms, mappings_by_song.get(pco_song_id, {}))
        if any(not state.matched for state in platform_state.values()):
            out.append(
                SongWithPlatforms(
                    pco_song_id=pco_song_id,
                    title=info["title"],
                    artist=info["artist"],
                    last_used_date=info["last_used_date"],
                    platforms=platform_state,
                )
            )
    return out


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
            "preview_url": r.preview_url,
            "external_url": r.external_url,
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


async def list_songs_with_mappings(
    db: AsyncSession,
    church_id: uuid.UUID,
) -> list[SongWithPlatforms]:
    """Return one row per PCO song that has at least one mapping on a connected platform.

    Mappings on platforms the church no longer has connected are ignored — a song that
    only has mappings on disconnected platforms will not appear here.
    """
    connected_platforms = await _get_connected_platforms(db, church_id)
    if not connected_platforms:
        return []

    result = await db.execute(
        select(SongMapping)
        .where(
            SongMapping.church_id == church_id,
            SongMapping.platform.in_(connected_platforms),
        )
        .order_by(SongMapping.created_at.desc())
    )
    mappings = list(result.scalars().all())

    by_song: dict[str, dict[str, SongMapping]] = {}
    song_meta: dict[str, tuple[str, str | None]] = {}
    for mapping in mappings:
        by_song.setdefault(mapping.pco_song_id, {})[mapping.platform] = mapping
        if mapping.pco_song_id not in song_meta:
            song_meta[mapping.pco_song_id] = (mapping.pco_song_title, mapping.pco_song_artist)

    out: list[SongWithPlatforms] = []
    for pco_song_id, mappings_by_platform in by_song.items():
        title, artist = song_meta[pco_song_id]
        out.append(
            SongWithPlatforms(
                pco_song_id=pco_song_id,
                title=title,
                artist=artist,
                last_used_date=None,
                platforms=_build_platform_state(connected_platforms, mappings_by_platform),
            )
        )
    return out


async def get_song_mappings(
    db: AsyncSession,
    church_id: uuid.UUID,
    pco_song_id: str,
) -> dict[str, PlatformMappingState]:
    """Return the per-platform mapping state for a single PCO song.

    The result is keyed by every connected streaming platform; platforms with no
    mapping are returned with `matched=False`. Mappings on disconnected platforms
    are ignored — same convention as `list_songs_with_mappings`.
    """
    connected_platforms = await _get_connected_platforms(db, church_id)
    if not connected_platforms:
        return {}

    result = await db.execute(
        select(SongMapping).where(
            SongMapping.church_id == church_id,
            SongMapping.pco_song_id == pco_song_id,
            SongMapping.platform.in_(connected_platforms),
        )
    )
    mappings_by_platform = {m.platform: m for m in result.scalars().all()}
    return _build_platform_state(connected_platforms, mappings_by_platform)


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
