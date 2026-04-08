"""Church settings endpoints."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_verified_email
from app.models.church import Church
from app.schemas.settings import ChurchSettingsResponse, ChurchSettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> ChurchSettingsResponse:
    """Return the current church playlist settings."""
    church_id = request.state.church_id
    result = await db.execute(select(Church).where(Church.id == church_id))
    church = result.scalar_one()
    return ChurchSettingsResponse(
        playlist_mode=church.playlist_mode,
        playlist_name_template=church.playlist_name_template,
        playlist_description_template=church.playlist_description_template,
    )


@router.patch("")
async def update_settings(
    body: ChurchSettingsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> ChurchSettingsResponse:
    """Partially update the church playlist settings."""
    church_id = request.state.church_id
    result = await db.execute(select(Church).where(Church.id == church_id))
    church = result.scalar_one()

    if body.playlist_mode is not None:
        church.playlist_mode = body.playlist_mode
    if body.playlist_name_template is not None:
        church.playlist_name_template = body.playlist_name_template
    if body.playlist_description_template is not None:
        church.playlist_description_template = body.playlist_description_template

    await db.flush()

    return ChurchSettingsResponse(
        playlist_mode=church.playlist_mode,
        playlist_name_template=church.playlist_name_template,
        playlist_description_template=church.playlist_description_template,
    )
