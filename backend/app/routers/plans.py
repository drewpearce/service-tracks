import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.pco_client import PcoApiError
from app.database import get_db
from app.dependencies import require_verified_email
from app.models.church import Church
from app.models.playlist import Playlist
from app.models.song_mapping import SongMapping
from app.rate_limit import church_id_key, limiter
from app.schemas.dashboard import PlanPlaylist, PlanSongWithMatch, PlansResponse, PlanWithSongs
from app.schemas.plans import SyncTriggerResponse
from app.services import pco_service, sync_service

router = APIRouter(prefix="/api/plans", tags=["plans"])


# ---------------------------------------------------------------------------
# GET /api/plans
# ---------------------------------------------------------------------------


@router.get("")
async def get_plans(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> PlansResponse:
    """Return upcoming plans with songs and match/playlist status."""
    church_id = request.state.church_id

    # Fetch upcoming plans from PCO
    try:
        plans = await pco_service.get_upcoming_plans_for_church(db, church_id)
    except PcoApiError as exc:
        raise HTTPException(status_code=502, detail="PCO API error.") from exc
    except ValueError:
        return PlansResponse(plans=[])

    if not plans:
        return PlansResponse(plans=[])

    # Fetch songs for all plans concurrently
    church_result = await db.execute(select(Church).where(Church.id == church_id))
    church = church_result.scalar_one_or_none()
    if church is None or church.pco_service_type_id is None:
        return PlansResponse(plans=[])

    pco_client = await pco_service.get_pco_client(db, church_id)

    async def fetch_songs(plan_id: str):
        try:
            return await pco_client.get_plan_songs(church.pco_service_type_id, plan_id)
        except PcoApiError:
            return []

    all_songs = await asyncio.gather(*[fetch_songs(p.id) for p in plans])

    # Fetch all song mappings for this church (for match checking)
    mappings_result = await db.execute(select(SongMapping).where(SongMapping.church_id == church_id))
    all_mappings = mappings_result.scalars().all()
    mapped_song_ids = {m.pco_song_id for m in all_mappings}

    # Fetch all playlists for this church
    playlists_result = await db.execute(select(Playlist).where(Playlist.church_id == church_id))
    all_playlists = playlists_result.scalars().all()
    # Index by pco_plan_id
    playlists_by_plan: dict[str, list[Playlist]] = {}
    for pl in all_playlists:
        playlists_by_plan.setdefault(pl.pco_plan_id, []).append(pl)

    result_plans: list[PlanWithSongs] = []
    for plan, songs in zip(plans, all_songs):
        plan_songs = [
            PlanSongWithMatch(
                pco_song_id=s.pco_song_id,
                title=s.title,
                matched=s.pco_song_id in mapped_song_ids,
            )
            for s in songs
        ]
        unmatched_count = sum(1 for s in plan_songs if not s.matched)

        plan_playlists = [
            PlanPlaylist(
                platform=pl.platform,
                status=pl.sync_status,
                url=pl.external_playlist_url,
                last_synced_at=(pl.last_synced_at.isoformat() if pl.last_synced_at else None),
                error_message=pl.error_message,
            )
            for pl in playlists_by_plan.get(plan.id, [])
        ]

        result_plans.append(
            PlanWithSongs(
                pco_plan_id=plan.id,
                date=plan.sort_date[:10],
                title=plan.title,
                songs=plan_songs,
                playlists=plan_playlists,
                unmatched_count=unmatched_count,
            )
        )

    return PlansResponse(plans=result_plans)


# ---------------------------------------------------------------------------
# POST /api/plans/{pco_plan_id}/sync
# ---------------------------------------------------------------------------


@router.post("/{pco_plan_id}/sync")
@limiter.limit("6/hour", key_func=church_id_key)
async def sync_plan(
    pco_plan_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> SyncTriggerResponse:
    church_id = request.state.church_id
    result = await sync_service.sync_plan(db, church_id, pco_plan_id, trigger="manual")
    return SyncTriggerResponse(**result.model_dump())
