"""Song matching endpoints — search, unmatched detection, and mapping CRUD."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.adapters.pco_client import PcoAuthError, PcoRateLimitError, PcoServerError
from app.adapters.spotify_adapter import SpotifyApiError, SpotifyAuthError, SpotifyRateLimitError
from app.database import get_db
from app.dependencies import require_verified_email
from app.rate_limit import limiter
from app.schemas.songs import (
    MappingsResponse,
    MatchRequest,
    MatchResponse,
    SearchResponse,
    SongMappingSchema,
    UnmatchedSongsResponse,
)
from app.services import song_service

router = APIRouter(prefix="/api/songs", tags=["songs"])

SUPPORTED_PLATFORMS = {"spotify"}


# ---------------------------------------------------------------------------
# GET /unmatched
# ---------------------------------------------------------------------------


@router.get("/unmatched")
async def unmatched_songs(
    request: Request,
    platform: str,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> UnmatchedSongsResponse:
    """Return songs from upcoming plans that don't have a mapping for the given platform."""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail="unsupported_platform")

    church_id = request.state.church_id

    try:
        unmatched = await song_service.get_unmatched_songs(db, church_id, platform)
    except ValueError as e:
        if str(e) == "pco_not_connected":
            raise HTTPException(status_code=400, detail="pco_not_connected") from e
        raise
    except PcoAuthError as exc:
        raise HTTPException(status_code=502, detail="PCO authentication error.") from exc
    except PcoRateLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"PCO rate limit exceeded. Retry after {exc.retry_after} seconds.",
        ) from exc
    except PcoServerError as exc:
        raise HTTPException(status_code=502, detail="PCO is currently unavailable.") from exc

    return UnmatchedSongsResponse(unmatched_songs=unmatched)


# ---------------------------------------------------------------------------
# GET /search
# ---------------------------------------------------------------------------


@router.get("/search")
async def search_songs(
    request: Request,
    platform: str,
    q: str,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> SearchResponse:
    """Search for tracks on the given streaming platform, with caching."""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail="unsupported_platform")

    if not q.strip():
        raise HTTPException(status_code=400, detail="query_empty")

    church_id = request.state.church_id

    try:
        results = await song_service.search_tracks(db, church_id, platform, q)
    except ValueError as e:
        if str(e) == "streaming_not_connected":
            raise HTTPException(status_code=400, detail="streaming_not_connected") from e
        raise
    except SpotifyAuthError as exc:
        raise HTTPException(status_code=502, detail="streaming_auth_error") from exc
    except SpotifyRateLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Spotify rate limit exceeded. Retry after {exc.retry_after} seconds.",
        ) from exc
    except SpotifyApiError as exc:
        raise HTTPException(status_code=502, detail=f"Spotify API error: {exc.message}") from exc

    return SearchResponse(results=results)


# ---------------------------------------------------------------------------
# POST /match
# ---------------------------------------------------------------------------


@router.post("/match", status_code=201)
@limiter.limit("30/minute")
async def match_song(
    body: MatchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> MatchResponse:
    """Create or update a song mapping."""
    church_id = request.state.church_id
    user_id = request.state.current_user.id

    mapping = await song_service.create_or_update_mapping(db, church_id, user_id, body)

    return MatchResponse(
        mapping_id=str(mapping.id),
        pco_song_title=mapping.pco_song_title,
        pco_song_artist=mapping.pco_song_artist,
        track_title=mapping.track_title,
        track_artist=mapping.track_artist,
        platform=mapping.platform,
    )


# ---------------------------------------------------------------------------
# GET /mappings
# ---------------------------------------------------------------------------


@router.get("/mappings")
async def get_mappings(
    request: Request,
    platform: str | None = None,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> MappingsResponse:
    """Return all song mappings for the authenticated church, optionally filtered by platform."""
    church_id = request.state.church_id

    mappings = await song_service.list_mappings(db, church_id, platform)

    return MappingsResponse(
        mappings=[
            SongMappingSchema(
                id=str(m.id),
                pco_song_id=m.pco_song_id,
                pco_song_title=m.pco_song_title,
                pco_song_artist=m.pco_song_artist,
                platform=m.platform,
                track_id=m.track_id,
                track_title=m.track_title,
                track_artist=m.track_artist,
            )
            for m in mappings
        ]
    )


# ---------------------------------------------------------------------------
# DELETE /mappings/{mapping_id}
# ---------------------------------------------------------------------------


@router.delete("/mappings/{mapping_id}", status_code=204)
async def delete_mapping_endpoint(
    mapping_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> Response:
    """Delete a song mapping by ID (tenant-isolated)."""
    church_id = request.state.church_id

    deleted = await song_service.delete_mapping(db, church_id, mapping_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="mapping_not_found")

    return Response(status_code=204)
