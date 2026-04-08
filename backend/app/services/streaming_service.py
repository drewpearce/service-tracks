"""Streaming service utilities: token refresh and connection helpers."""

from datetime import datetime, timedelta, timezone

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.streaming_connection import StreamingConnection
from app.utils.encryption import decrypt, encrypt

logger = structlog.get_logger(__name__)


class SpotifyTokenError(Exception):
    """Raised when Spotify token refresh fails."""

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
