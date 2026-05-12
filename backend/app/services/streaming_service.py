"""Streaming service utilities: token refresh and connection helpers."""

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.playlist import Playlist
from app.models.streaming_connection import StreamingConnection
from app.models.streaming_settings import (
    DEFAULT_DESCRIPTION_TEMPLATE,
    DEFAULT_NAME_TEMPLATE,
    DEFAULT_PLAYLIST_MODE,
    StreamingSettings,
)
from app.utils.encryption import decrypt, encrypt

logger = structlog.get_logger(__name__)


class SpotifyTokenError(Exception):
    """Raised when Spotify token refresh fails."""

    pass


class YouTubeTokenError(Exception):
    """Raised when YouTube (Google) token refresh fails."""

    pass


async def refresh_spotify_token(
    db: AsyncSession,
    connection: StreamingConnection,
) -> str:
    """Refresh a Spotify access token. Returns the new access token (plaintext).

    CRITICAL: Preserves existing refresh_token when Spotify does not return a new one.
    Updates the streaming_connection row with new encrypted tokens and expiry.
    """
    existing_refresh_token = decrypt(connection.refresh_token_encrypted)

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": existing_refresh_token,
                "client_id": settings.SPOTIFY_CLIENT_ID,
                "client_secret": settings.SPOTIFY_CLIENT_SECRET,
            },
        )

    if response.status_code != 200:
        logger.error("spotify_token_refresh_failed", status_code=response.status_code)
        connection.status = "error"
        await db.flush()
        raise SpotifyTokenError("Token refresh failed")

    data = response.json()
    new_access_token = data["access_token"]
    # CRITICAL: preserve existing refresh token if Spotify doesn't return a new one
    new_refresh_token = data.get("refresh_token") or existing_refresh_token
    expires_in = data["expires_in"]

    connection.access_token_encrypted = encrypt(new_access_token)
    connection.refresh_token_encrypted = encrypt(new_refresh_token)
    connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    connection.status = "active"
    await db.flush()

    return new_access_token


async def revoke_youtube_token(connection: StreamingConnection) -> bool:
    """Revoke a YouTube (Google) refresh token at the provider.

    Best-effort: returns True on success, False on failure. Caller still deletes
    the local connection regardless.
    """
    try:
        refresh_token = decrypt(connection.refresh_token_encrypted)
    except Exception:
        logger.warning("youtube_revoke_decrypt_failed", connection_id=str(connection.id))
        return False

    if not refresh_token or refresh_token == "pending":
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": refresh_token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as e:
        logger.warning("youtube_revoke_request_failed", error=str(e))
        return False

    if response.status_code == 200:
        return True
    logger.warning(
        "youtube_revoke_non_200",
        status_code=response.status_code,
        body=response.text,
    )
    return False


async def get_or_create_settings(
    db: AsyncSession,
    church_id: uuid.UUID,
    platform: str,
) -> StreamingSettings:
    """Return the StreamingSettings row for (church, platform), creating defaults if absent."""
    result = await db.execute(
        select(StreamingSettings).where(
            StreamingSettings.church_id == church_id,
            StreamingSettings.platform == platform,
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row

    row = StreamingSettings(
        church_id=church_id,
        platform=platform,
        playlist_mode=DEFAULT_PLAYLIST_MODE,
        playlist_name_template=DEFAULT_NAME_TEMPLATE,
        playlist_description_template=DEFAULT_DESCRIPTION_TEMPLATE,
    )
    db.add(row)
    await db.flush()
    return row


async def reset_platform(
    db: AsyncSession,
    church_id: uuid.UUID,
    platform: str,
) -> None:
    """Forget all local playlist state for a platform and reset templates to defaults.

    Deletes Playlist rows for (church, platform) and resets the streaming_settings row
    to defaults (creating it if missing). Leaves the StreamingConnection intact.
    """
    await db.execute(
        delete(Playlist).where(
            Playlist.church_id == church_id,
            Playlist.platform == platform,
        )
    )
    row = await get_or_create_settings(db, church_id, platform)
    row.playlist_mode = DEFAULT_PLAYLIST_MODE
    row.playlist_name_template = DEFAULT_NAME_TEMPLATE
    row.playlist_description_template = DEFAULT_DESCRIPTION_TEMPLATE
    await db.flush()


async def disconnect_platform(
    db: AsyncSession,
    church_id: uuid.UUID,
    platform: str,
) -> bool:
    """Disconnect a streaming platform: revoke at provider (where possible) and delete local state.

    Returns True if a connection was found and removed, False otherwise. For YouTube,
    attempts a best-effort token revocation at Google; Spotify has no revocation
    endpoint so we only drop the local row. Deletes Playlist rows, the streaming_settings
    row, and the StreamingConnection row regardless of revocation outcome.
    """
    result = await db.execute(
        select(StreamingConnection).where(
            StreamingConnection.church_id == church_id,
            StreamingConnection.platform == platform,
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        return False

    if platform == "youtube":
        await revoke_youtube_token(connection)
    # Spotify: no public revocation endpoint. Dropping the local row makes the
    # tokens unusable from our side; users can revoke app access via their
    # Spotify account settings if desired.

    await db.execute(
        delete(Playlist).where(
            Playlist.church_id == church_id,
            Playlist.platform == platform,
        )
    )
    await db.execute(
        delete(StreamingSettings).where(
            StreamingSettings.church_id == church_id,
            StreamingSettings.platform == platform,
        )
    )
    await db.delete(connection)
    await db.flush()
    return True


async def refresh_youtube_token(
    db: AsyncSession,
    connection: StreamingConnection,
) -> str:
    """Refresh a YouTube (Google) access token. Returns the new access token (plaintext).

    Google's token endpoint rarely returns a new refresh_token, so we preserve
    the existing one when one isn't returned.
    """
    existing_refresh_token = decrypt(connection.refresh_token_encrypted)

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": existing_refresh_token,
                "client_id": settings.YOUTUBE_CLIENT_ID,
                "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            },
        )

    if response.status_code != 200:
        logger.error("youtube_token_refresh_failed", status_code=response.status_code)
        connection.status = "error"
        await db.flush()
        raise YouTubeTokenError("Token refresh failed")

    data = response.json()
    new_access_token = data["access_token"]
    new_refresh_token = data.get("refresh_token") or existing_refresh_token
    expires_in = data["expires_in"]

    connection.access_token_encrypted = encrypt(new_access_token)
    connection.refresh_token_encrypted = encrypt(new_refresh_token)
    connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    connection.status = "active"
    await db.flush()

    return new_access_token
