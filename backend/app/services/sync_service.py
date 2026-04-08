"""Core sync engine — sync_plan() and sync_church().

sync_plan() uses db.flush() (not db.commit()); the caller manages the transaction boundary.
"""

import uuid
from datetime import date, datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.pco_client import PcoApiError
from app.adapters.streaming import get_streaming_adapter
from app.models.church import Church
from app.models.playlist import Playlist
from app.models.song_mapping import SongMapping
from app.models.streaming_connection import StreamingConnection
from app.models.sync_log import SyncLog
from app.schemas.sync import PlatformSyncResult, SyncResult
from app.services import pco_service
from app.utils.playlist_templates import render_template

logger = structlog.get_logger(__name__)


async def sync_plan(
    db: AsyncSession,
    church_id: uuid.UUID,
    pco_plan_id: str,
    trigger: str,
    plan_date: date | None = None,
    plan_title: str | None = None,
) -> SyncResult:
    """Sync a single PCO plan to all active streaming connections for a church.

    Uses db.flush() — the caller manages the transaction boundary.
    """
    started_at = datetime.now(timezone.utc)

    # Step 2: Load church record
    result = await db.execute(select(Church).where(Church.id == church_id))
    church = result.scalar_one_or_none()
    if church is None:
        logger.error("sync_plan_church_not_found", church_id=str(church_id))
        return SyncResult(
            sync_status="error",
            songs_total=0,
            songs_matched=0,
            songs_unmatched=0,
            platforms=[],
        )

    # Step 3: Load active streaming connections
    result = await db.execute(
        select(StreamingConnection).where(
            StreamingConnection.church_id == church_id,
            StreamingConnection.status == "active",
        )
    )
    streaming_connections = result.scalars().all()

    if not streaming_connections:
        logger.warning("sync_plan_no_streaming_connections", church_id=str(church_id))
        sync_log = SyncLog(
            church_id=church_id,
            playlist_id=None,
            sync_trigger=trigger,
            status="skipped",
            songs_total=0,
            songs_matched=0,
            songs_unmatched=0,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(sync_log)
        await db.flush()
        return SyncResult(
            sync_status="skipped",
            songs_total=0,
            songs_matched=0,
            songs_unmatched=0,
            platforms=[],
        )

    # Step 3b: Fetch plan metadata from PCO if plan_date wasn't provided by the caller.
    # The scheduler always passes plan_date; the manual HTTP trigger does not.
    # We also pick up plan_title here so templates like {title} work on manual syncs.
    if plan_date is None:
        plan_meta = await pco_service.get_plan_for_church(db, church_id, pco_plan_id)
        if plan_meta is not None:
            if plan_meta.sort_date:
                try:
                    # PCO returns sort_date as "YYYY-MM-DDThh:mm:ssZ" or "YYYY-MM-DD";
                    # slice to first 10 chars to handle both formats.
                    plan_date = date.fromisoformat(plan_meta.sort_date[:10])
                except ValueError:
                    pass
            plan_title = plan_title or plan_meta.title or None

    # Step 4: Fetch plan songs via pco_service
    try:
        songs = await pco_service.get_plan_songs_for_church(db, church_id, pco_plan_id)
    except PcoApiError as e:
        logger.error("sync_plan_pco_error", church_id=str(church_id), pco_plan_id=pco_plan_id, error=str(e))
        sync_log = SyncLog(
            church_id=church_id,
            playlist_id=None,
            sync_trigger=trigger,
            status="error",
            songs_total=0,
            songs_matched=0,
            songs_unmatched=0,
            error_message=str(e),
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(sync_log)
        await db.flush()
        return SyncResult(
            sync_status="error",
            songs_total=0,
            songs_matched=0,
            songs_unmatched=0,
            platforms=[],
        )

    # Step 5: For each streaming connection, resolve mappings
    # matched_song_ids tracks which pco_song_ids have at least one platform match
    matched_song_ids: set[str] = set()

    # Per-connection mapping results (track_ids in plan order)
    connection_matched_track_ids: dict[str, list[str]] = {}

    for connection in streaming_connections:
        platform = connection.platform
        matched_track_ids = []

        for song in songs:
            result = await db.execute(
                select(SongMapping).where(
                    SongMapping.church_id == church_id,
                    SongMapping.pco_song_id == song.pco_song_id,
                    SongMapping.platform == platform,
                )
            )
            mapping = result.scalar_one_or_none()
            if mapping:
                matched_track_ids.append(mapping.track_id)
                matched_song_ids.add(song.pco_song_id)

        connection_matched_track_ids[str(connection.id)] = matched_track_ids

    # Step 6: For each streaming connection, sync the playlist
    platform_results = []
    last_playlist = None

    for connection in streaming_connections:
        platform = connection.platform
        matched_track_ids = connection_matched_track_ids[str(connection.id)]

        playlist = None  # Initialize before try block to avoid NameError in except handler
        try:
            adapter = get_streaming_adapter(connection.platform, connection, db=db)

            # a. Determine playlist mode and lookup key
            playlist_mode = church.playlist_mode  # "shared" or "per_plan"
            lookup_plan_id = "__shared__" if playlist_mode == "shared" else pco_plan_id

            rendered_name = render_template(
                church.playlist_name_template,
                plan_date=plan_date,
                plan_title=plan_title,
                church_name=church.name,
            )
            rendered_description = render_template(
                church.playlist_description_template,
                plan_date=plan_date,
                plan_title=plan_title,
                church_name=church.name,
            )

            result = await db.execute(
                select(Playlist).where(
                    Playlist.church_id == church_id,
                    Playlist.pco_plan_id == lookup_plan_id,
                    Playlist.platform == connection.platform,
                )
            )
            playlist = result.scalar_one_or_none()

            if playlist is None:
                # For shared mode, try to connect to an existing playlist with
                # the same name before creating a new one — avoids duplicates
                # when the user already has a playlist by this name.
                existing = None
                if playlist_mode == "shared":
                    existing = await adapter.find_playlist_by_name(rendered_name)

                if existing is not None:
                    playlist_info = existing
                else:
                    playlist_info = await adapter.create_playlist(
                        name=rendered_name,
                        description=rendered_description,
                    )
                playlist = Playlist(
                    church_id=church_id,
                    pco_plan_id=lookup_plan_id,
                    pco_plan_date=plan_date or date.today(),
                    platform=connection.platform,
                    external_playlist_id=playlist_info.external_id,
                    external_playlist_url=playlist_info.url,
                    sync_status="pending",
                )
                db.add(playlist)
                await db.flush()
            else:
                if playlist_mode == "shared":
                    # Update name/description so date template stays current
                    await adapter.update_playlist_details(
                        playlist.external_playlist_id, rendered_name, rendered_description
                    )
                    playlist.pco_plan_date = plan_date or date.today()

            # b. Replace tracks if any matched
            if matched_track_ids:
                await adapter.replace_playlist_tracks(playlist.external_playlist_id, matched_track_ids)
                playlist.last_synced_at = datetime.now(timezone.utc)
                playlist.sync_status = "synced"
                playlist.last_known_track_ids = matched_track_ids
                playlist.error_message = None
            else:
                # c. No matched tracks
                playlist.sync_status = "pending"

            await db.flush()
            last_playlist = playlist

            platform_results.append(
                PlatformSyncResult(
                    platform=connection.platform,
                    sync_status=playlist.sync_status,
                    playlist_url=playlist.external_playlist_url,
                )
            )

        except Exception as e:
            # Streaming API failure: catch, log, do NOT raise
            logger.error(
                "sync_streaming_error",
                church_id=str(church_id),
                platform=connection.platform,
                error=str(e),
            )
            if playlist:
                playlist.sync_status = "error"
                playlist.error_message = str(e)
                await db.flush()

            platform_results.append(
                PlatformSyncResult(
                    platform=connection.platform,
                    sync_status="error",
                    error_message=str(e),
                )
            )

    # Step 6b: Compute aggregate matched count
    songs_matched_count = len(matched_song_ids)

    # Step 7: Write sync_log entry
    completed_at = datetime.now(timezone.utc)

    # Determine overall status
    statuses = [pr.sync_status for pr in platform_results]
    if all(s == "synced" for s in statuses):
        overall_status = "synced"
    elif all(s == "error" for s in statuses):
        overall_status = "error"
    elif any(s == "synced" for s in statuses):
        overall_status = "partial"
    else:
        overall_status = "pending"

    sync_log = SyncLog(
        church_id=church_id,
        playlist_id=last_playlist.id if last_playlist and len(streaming_connections) == 1 else None,
        sync_trigger=trigger,
        status=overall_status,
        songs_total=len(songs),
        songs_matched=songs_matched_count,
        songs_unmatched=len(songs) - songs_matched_count,
        started_at=started_at,
        completed_at=completed_at,
    )
    db.add(sync_log)
    await db.flush()

    # Step 8: Return SyncResult
    return SyncResult(
        sync_status=overall_status,
        songs_total=len(songs),
        songs_matched=songs_matched_count,
        songs_unmatched=len(songs) - songs_matched_count,
        platforms=platform_results,
    )


async def sync_church(
    db: AsyncSession,
    church_id: uuid.UUID,
    trigger: str = "poll",
) -> list[SyncResult]:
    """Sync all upcoming plans for a church.

    Returns a list of SyncResults, one per plan.
    """
    try:
        plans = await pco_service.get_upcoming_plans_for_church(db, church_id)
    except PcoApiError:
        logger.error("sync_church_pco_error", church_id=str(church_id))
        return []

    results = []
    for plan in plans:
        plan_date = date.fromisoformat(plan.sort_date[:10])
        result = await sync_plan(
            db,
            church_id,
            plan.id,
            trigger,
            plan_date=plan_date,
            plan_title=plan.title,
        )
        results.append(result)

    return results
