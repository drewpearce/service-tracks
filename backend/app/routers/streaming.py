"""Streaming integration endpoints: Spotify OAuth flow and connection status."""

import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import require_verified_email
from app.models.streaming_connection import StreamingConnection
from app.schemas.streaming import (
    SpotifyAuthorizeResponse,
    StreamingConnectionStatus,
    StreamingStatusResponse,
    YouTubeAuthorizeResponse,
)
from app.utils.encryption import decrypt, encrypt

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/streaming", tags=["streaming"])

SPOTIFY_SCOPES = "playlist-modify-public playlist-modify-private playlist-read-private"

YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube"


# ---------------------------------------------------------------------------
# GET /spotify/authorize
# ---------------------------------------------------------------------------


@router.get("/spotify/authorize")
async def spotify_authorize(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> SpotifyAuthorizeResponse:
    """Begin Spotify OAuth flow. Returns the authorization URL."""
    church_id = request.state.church_id

    state = secrets.token_urlsafe(16)

    # Upsert pending streaming_connection to store the OAuth state
    result = await db.execute(
        select(StreamingConnection).where(
            StreamingConnection.church_id == church_id,
            StreamingConnection.platform == "spotify",
        )
    )
    conn = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    state_expiry = now + timedelta(minutes=10)

    if conn is not None:
        conn.status = "pending"
        conn.access_token_encrypted = encrypt(state)
        conn.refresh_token_encrypted = encrypt("pending")
        conn.token_expires_at = state_expiry
        conn.external_user_id = "pending"
    else:
        conn = StreamingConnection(
            church_id=church_id,
            platform="spotify",
            status="pending",
            access_token_encrypted=encrypt(state),
            refresh_token_encrypted=encrypt("pending"),
            token_expires_at=state_expiry,
            external_user_id="pending",
        )
        db.add(conn)

    await db.flush()

    params = {
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "scope": SPOTIFY_SCOPES,
        "state": state,
    }
    authorization_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"

    return SpotifyAuthorizeResponse(authorization_url=authorization_url)


# ---------------------------------------------------------------------------
# GET /spotify/callback
# ---------------------------------------------------------------------------


@router.get("/spotify/callback")
async def spotify_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    code: str = "",
    state: str = "",
    error: str | None = None,
) -> RedirectResponse:
    """Handle Spotify OAuth callback. Validates state, exchanges code for tokens.

    This endpoint is exempt from session auth because the browser navigates here
    directly from Spotify (127.0.0.1 vs localhost cookie domain mismatch). The
    OAuth state parameter is the security mechanism — we find the church by
    matching state against all pending connections.
    """
    error_redirect = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/dashboard?spotify=error",
        status_code=302,
    )

    # User denied authorization
    if error:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard?spotify=denied",
            status_code=302,
        )

    if not state:
        return error_redirect

    # Find the pending connection by matching the encrypted state value.
    # We can't filter by church_id here because the session cookie isn't
    # available on this redirect (different host from the frontend proxy).
    result = await db.execute(
        select(StreamingConnection).where(
            StreamingConnection.platform == "spotify",
            StreamingConnection.status == "pending",
        )
    )
    pending_conns = result.scalars().all()

    conn = None
    for pending in pending_conns:
        try:
            if decrypt(pending.access_token_encrypted) == state:
                conn = pending
                break
        except Exception:
            continue

    if conn is None:
        logger.warning("spotify_callback_no_pending_connection_for_state")
        return error_redirect

    church_id = conn.church_id

    now = datetime.now(timezone.utc)

    # Check state has not expired
    token_expires_at = conn.token_expires_at
    if token_expires_at.tzinfo is None:
        token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

    if now > token_expires_at:
        logger.warning("spotify_callback_state_expired", church_id=str(church_id))
        return error_redirect

    # Exchange authorization code for tokens
    async with httpx.AsyncClient(timeout=15.0) as http_client:
        token_response = await http_client.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
                "client_id": settings.SPOTIFY_CLIENT_ID,
                "client_secret": settings.SPOTIFY_CLIENT_SECRET,
            },
        )

    if token_response.status_code != 200:
        logger.error(
            "spotify_token_exchange_failed",
            status_code=token_response.status_code,
            church_id=str(church_id),
        )
        return error_redirect

    token_data = token_response.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_in = token_data["expires_in"]

    # Fetch Spotify user profile
    async with httpx.AsyncClient(timeout=15.0) as http_client:
        profile_response = await http_client.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if profile_response.status_code != 200:
        logger.error(
            "spotify_profile_fetch_failed",
            status_code=profile_response.status_code,
            church_id=str(church_id),
        )
        return error_redirect

    spotify_user_id = profile_response.json()["id"]

    # Update the connection with real tokens
    conn.access_token_encrypted = encrypt(access_token)
    conn.refresh_token_encrypted = encrypt(refresh_token)
    conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    conn.external_user_id = spotify_user_id
    conn.status = "active"

    await db.flush()

    logger.info("spotify_connected", church_id=str(church_id), spotify_user_id=spotify_user_id)

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/dashboard?spotify=connected",
        status_code=302,
    )


# ---------------------------------------------------------------------------
# GET /youtube/authorize
# ---------------------------------------------------------------------------


@router.get("/youtube/authorize")
async def youtube_authorize(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> YouTubeAuthorizeResponse:
    """Begin YouTube OAuth flow. Returns the authorization URL."""
    church_id = request.state.church_id

    state = secrets.token_urlsafe(16)

    result = await db.execute(
        select(StreamingConnection).where(
            StreamingConnection.church_id == church_id,
            StreamingConnection.platform == "youtube",
        )
    )
    conn = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    state_expiry = now + timedelta(minutes=10)

    if conn is not None:
        conn.status = "pending"
        conn.access_token_encrypted = encrypt(state)
        conn.refresh_token_encrypted = encrypt("pending")
        conn.token_expires_at = state_expiry
        conn.external_user_id = "pending"
    else:
        conn = StreamingConnection(
            church_id=church_id,
            platform="youtube",
            status="pending",
            access_token_encrypted=encrypt(state),
            refresh_token_encrypted=encrypt("pending"),
            token_expires_at=state_expiry,
            external_user_id="pending",
        )
        db.add(conn)

    await db.flush()

    params = {
        "client_id": settings.YOUTUBE_CLIENT_ID,
        "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
        "response_type": "code",
        "scope": YOUTUBE_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    authorization_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    return YouTubeAuthorizeResponse(authorization_url=authorization_url)


# ---------------------------------------------------------------------------
# GET /youtube/callback
# ---------------------------------------------------------------------------


@router.get("/youtube/callback")
async def youtube_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    code: str = "",
    state: str = "",
    error: str | None = None,
) -> RedirectResponse:
    """Handle YouTube OAuth callback. Validates state, exchanges code for tokens.

    Exempt from session auth — matched to a pending connection via OAuth state.
    """
    error_redirect = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/dashboard?youtube=error",
        status_code=302,
    )

    if error:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard?youtube=denied",
            status_code=302,
        )

    if not state:
        return error_redirect

    result = await db.execute(
        select(StreamingConnection).where(
            StreamingConnection.platform == "youtube",
            StreamingConnection.status == "pending",
        )
    )
    pending_conns = result.scalars().all()

    conn = None
    for pending in pending_conns:
        try:
            if decrypt(pending.access_token_encrypted) == state:
                conn = pending
                break
        except Exception:
            continue

    if conn is None:
        logger.warning("youtube_callback_no_pending_connection_for_state")
        return error_redirect

    church_id = conn.church_id

    now = datetime.now(timezone.utc)

    token_expires_at = conn.token_expires_at
    if token_expires_at.tzinfo is None:
        token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

    if now > token_expires_at:
        logger.warning("youtube_callback_state_expired", church_id=str(church_id))
        return error_redirect

    # Exchange authorization code for tokens
    async with httpx.AsyncClient(timeout=15.0) as http_client:
        token_response = await http_client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
                "client_id": settings.YOUTUBE_CLIENT_ID,
                "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            },
        )

    if token_response.status_code != 200:
        logger.error(
            "youtube_token_exchange_failed",
            status_code=token_response.status_code,
            church_id=str(church_id),
        )
        return error_redirect

    token_data = token_response.json()
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data["expires_in"]

    # Fetch channel info to get external_user_id
    async with httpx.AsyncClient(timeout=15.0) as http_client:
        channel_response = await http_client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "snippet", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if channel_response.status_code != 200:
        logger.error(
            "youtube_channel_fetch_failed",
            status_code=channel_response.status_code,
            church_id=str(church_id),
        )
        return error_redirect

    channel_items = channel_response.json().get("items", [])
    if not channel_items:
        logger.error("youtube_channel_empty", church_id=str(church_id))
        return error_redirect

    youtube_channel_id = channel_items[0]["id"]

    conn.access_token_encrypted = encrypt(access_token)
    conn.refresh_token_encrypted = encrypt(refresh_token)
    conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    conn.external_user_id = youtube_channel_id
    conn.status = "active"

    await db.flush()

    logger.info("youtube_connected", church_id=str(church_id), youtube_channel_id=youtube_channel_id)

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/dashboard?youtube=connected",
        status_code=302,
    )


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------


@router.get("/status")
async def streaming_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _verified: None = Depends(require_verified_email),
) -> StreamingStatusResponse:
    """Return all active streaming connections for the authenticated church."""
    church_id = request.state.church_id

    result = await db.execute(
        select(StreamingConnection).where(
            StreamingConnection.church_id == church_id,
            StreamingConnection.status != "pending",
        )
    )
    connections = result.scalars().all()

    return StreamingStatusResponse(
        connections=[
            StreamingConnectionStatus(
                platform=conn.platform,
                connected=(conn.status == "active"),
                status=conn.status,
                external_user_id=conn.external_user_id,
            )
            for conn in connections
        ]
    )
