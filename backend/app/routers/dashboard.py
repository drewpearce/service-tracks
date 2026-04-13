"""Dashboard aggregated endpoint."""

import asyncio

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.pco_client import PcoApiError
from app.database import get_db
from app.dependencies import require_auth
from app.models.church import Church
from app.models.pco_connection import PcoConnection
from app.models.playlist import Playlist
from app.models.song_mapping import SongMapping
from app.models.streaming_connection import StreamingConnection
from app.models.sync_log import SyncLog
from app.schemas.dashboard import (
    DashboardResponse,
    PlanPlaylist,
    PlanSongWithMatch,
    PlanWithSongs,
    SyncLogEntry,
)
from app.schemas.streaming import StreamingConnectionStatus
from app.services import pco_service

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard")
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_auth),
) -> DashboardResponse:
    """Return aggregated dashboard data for the authenticated church."""
    church_id = request.state.church_id

    # Fetch church
    church_result = await db.execute(select(Church).where(Church.id == church_id))
    church = church_result.scalar_one()

    # Fetch PCO connection
    pco_conn_result = await db.execute(select(PcoConnection).where(PcoConnection.church_id == church_id))
    pco_conn = pco_conn_result.scalar_one_or_none()
    pco_connected = pco_conn is not None and pco_conn.status == "active"
    service_type_selected = church.pco_service_type_id is not None

    # Fetch streaming connections
    streaming_result = await db.execute(select(StreamingConnection).where(StreamingConnection.church_id == church_id))
    streaming_conns = streaming_result.scalars().all()
    streaming_connections = [
        StreamingConnectionStatus(
            platform=sc.platform,
            connected=sc.status == "active",
            status=sc.status,
            external_user_id=sc.external_user_id,
        )
        for sc in streaming_conns
    ]

    # Fetch upcoming plans (only if PCO connected and service type configured)
    upcoming_plans: list[PlanWithSongs] = []
    unmatched_song_count = 0

    if pco_connected and service_type_selected:
        try:
            plans = await pco_service.get_upcoming_plans_for_church(db, church_id)

            if plans:
                pco_client = await pco_service.get_pco_client(db, church_id)

                async def fetch_songs(plan_id: str):
                    try:
                        return await pco_client.get_plan_songs(church.pco_service_type_id, plan_id)
                    except PcoApiError:
                        return []

                all_songs = await asyncio.gather(*[fetch_songs(p.id) for p in plans])

                # Song mappings for match checking
                mappings_result = await db.execute(select(SongMapping).where(SongMapping.church_id == church_id))
                all_mappings = mappings_result.scalars().all()
                mapped_song_ids = {m.pco_song_id for m in all_mappings}

                # Playlists indexed by plan id
                playlists_result = await db.execute(select(Playlist).where(Playlist.church_id == church_id))
                all_playlists = playlists_result.scalars().all()
                playlists_by_plan: dict[str, list[Playlist]] = {}
                for pl in all_playlists:
                    playlists_by_plan.setdefault(pl.pco_plan_id, []).append(pl)

                for plan, songs in zip(plans, all_songs):
                    plan_songs = [
                        PlanSongWithMatch(
                            pco_song_id=s.pco_song_id,
                            title=s.title,
                            matched=s.pco_song_id in mapped_song_ids,
                        )
                        for s in songs
                    ]
                    unmatched_in_plan = sum(1 for s in plan_songs if not s.matched)
                    unmatched_song_count += unmatched_in_plan

                    # Look up playlists using the same key the sync engine uses
                    lookup_key = "__shared__" if church.playlist_mode == "shared" else plan.id
                    plan_playlist_rows = playlists_by_plan.get(lookup_key, [])
                    plan_playlists = [
                        PlanPlaylist(
                            platform=pl.platform,
                            status=pl.sync_status,
                            url=pl.external_playlist_url,
                            last_synced_at=(pl.last_synced_at.isoformat() if pl.last_synced_at else None),
                        )
                        for pl in plan_playlist_rows
                    ]

                    upcoming_plans.append(
                        PlanWithSongs(
                            pco_plan_id=plan.id,
                            date=plan.sort_date[:10],
                            title=plan.title,
                            songs=plan_songs,
                            playlists=plan_playlists,
                            unmatched_count=unmatched_in_plan,
                        )
                    )
        except (PcoApiError, ValueError):
            # Graceful degradation: return empty plans if PCO call fails
            pass

    # Fetch recent syncs (last 5, ordered by most recent first)
    sync_log_result = await db.execute(
        select(SyncLog).where(SyncLog.church_id == church_id).order_by(SyncLog.started_at.desc()).limit(5)
    )
    sync_logs = sync_log_result.scalars().all()
    recent_syncs = [
        SyncLogEntry(
            id=str(sl.id),
            sync_trigger=sl.sync_trigger,
            status=sl.status,
            songs_total=sl.songs_total,
            songs_matched=sl.songs_matched,
            songs_unmatched=sl.songs_unmatched,
            started_at=sl.started_at.isoformat(),
            completed_at=(sl.completed_at.isoformat() if sl.completed_at else None),
        )
        for sl in sync_logs
    ]

    return DashboardResponse(
        church_name=church.name,
        pco_connected=pco_connected,
        service_type_selected=service_type_selected,
        streaming_connections=streaming_connections,
        upcoming_plans=upcoming_plans,
        unmatched_song_count=unmatched_song_count,
        recent_syncs=recent_syncs,
    )
