"""Streaming OAuth endpoint integration tests — Epic 5.

Tests use real PostgreSQL (service_tracks_test DB) with per-test transaction rollback.
Outbound Spotify HTTP calls are mocked via respx.
asyncio_mode = "auto" (set in pyproject.toml) makes all async test functions run automatically.
"""

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import respx
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.church_user import ChurchUser
from app.models.streaming_connection import StreamingConnection
from app.utils.encryption import decrypt, encrypt
from tests.fixtures.spotify_responses import (
    SPOTIFY_TOKEN_RESPONSE,
    SPOTIFY_USER_PROFILE_RESPONSE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def get_verified_user_church_id(db: AsyncSession) -> uuid.UUID:
    """Return the church_id of the verified test user."""
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = result.scalar_one()
    return user.church_id


# ---------------------------------------------------------------------------
# GET /api/streaming/spotify/authorize
# ---------------------------------------------------------------------------


async def test_spotify_authorize_returns_auth_url(verified_authenticated_client: AsyncClient):
    response = await verified_authenticated_client.get("/api/streaming/spotify/authorize")

    assert response.status_code == 200
    body = response.json()
    assert "authorization_url" in body

    parsed = urlparse(body["authorization_url"])
    assert parsed.netloc == "accounts.spotify.com"
    assert parsed.path == "/authorize"

    # parse_qs drops blank values by default; use keep_blank_values=True so
    # client_id is present even when SPOTIFY_CLIENT_ID is empty in test settings
    params = parse_qs(parsed.query, keep_blank_values=True)
    assert "client_id" in params
    assert params["response_type"] == ["code"]
    assert "redirect_uri" in params
    assert "state" in params
    # Check all 3 required scopes are present in the scope string
    scope_str = params["scope"][0]
    assert "playlist-modify-public" in scope_str
    assert "playlist-modify-private" in scope_str
    assert "playlist-read-private" in scope_str


async def test_spotify_authorize_creates_pending_connection(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    church_id = await get_verified_user_church_id(db)

    await verified_authenticated_client.get("/api/streaming/spotify/authorize")

    result = await db.execute(
        select(StreamingConnection).where(
            StreamingConnection.church_id == church_id,
            StreamingConnection.platform == "spotify",
            StreamingConnection.status == "pending",
        )
    )
    conn = result.scalar_one_or_none()
    assert conn is not None
    assert conn.external_user_id == "pending"


# ---------------------------------------------------------------------------
# GET /api/streaming/spotify/callback
# ---------------------------------------------------------------------------


@respx.mock
async def test_spotify_callback_success(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    # Step 1: Get the state by calling authorize
    auth_response = await verified_authenticated_client.get("/api/streaming/spotify/authorize")
    auth_url = auth_response.json()["authorization_url"]
    parsed = urlparse(auth_url)
    state = parse_qs(parsed.query)["state"][0]

    # Step 2: Mock Spotify outbound HTTP calls
    respx.post("https://accounts.spotify.com/api/token").mock(
        return_value=Response(200, json=SPOTIFY_TOKEN_RESPONSE)
    )
    respx.get("https://api.spotify.com/v1/me").mock(
        return_value=Response(200, json=SPOTIFY_USER_PROFILE_RESPONSE)
    )

    # Step 3: Call the callback
    response = await verified_authenticated_client.get(
        f"/api/streaming/spotify/callback?code=test_code&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "dashboard" in response.headers["location"]
    assert "spotify=connected" in response.headers["location"]

    # Verify DB was updated
    church_id = await get_verified_user_church_id(db)
    result = await db.execute(
        select(StreamingConnection).where(
            StreamingConnection.church_id == church_id,
            StreamingConnection.platform == "spotify",
        )
    )
    conn = result.scalar_one()
    assert conn.status == "active"
    assert conn.external_user_id == SPOTIFY_USER_PROFILE_RESPONSE["id"]
    assert decrypt(conn.access_token_encrypted) == SPOTIFY_TOKEN_RESPONSE["access_token"]
    assert decrypt(conn.refresh_token_encrypted) == SPOTIFY_TOKEN_RESPONSE["refresh_token"]


async def test_spotify_callback_invalid_state(
    verified_authenticated_client: AsyncClient,
):
    # Call authorize to create a pending connection
    await verified_authenticated_client.get("/api/streaming/spotify/authorize")

    # Call callback with wrong state
    response = await verified_authenticated_client.get(
        "/api/streaming/spotify/callback?code=test_code&state=wrong_state_value",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "spotify=error" in response.headers["location"]


async def test_spotify_callback_no_pending_connection(
    verified_authenticated_client: AsyncClient,
):
    # Call callback without first calling authorize
    response = await verified_authenticated_client.get(
        "/api/streaming/spotify/callback?code=test_code&state=some_state",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "spotify=error" in response.headers["location"]


async def test_spotify_callback_user_denied(
    verified_authenticated_client: AsyncClient,
):
    response = await verified_authenticated_client.get(
        "/api/streaming/spotify/callback?error=access_denied&state=some_state",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "spotify=denied" in response.headers["location"]


# ---------------------------------------------------------------------------
# GET /api/streaming/status
# ---------------------------------------------------------------------------


async def test_spotify_status_no_connections(verified_authenticated_client: AsyncClient):
    response = await verified_authenticated_client.get("/api/streaming/status")

    assert response.status_code == 200
    body = response.json()
    assert body["connections"] == []


async def test_spotify_status_with_active_connection(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    church_id = await get_verified_user_church_id(db)

    # Insert an active connection directly
    conn = StreamingConnection(
        church_id=church_id,
        platform="spotify",
        access_token_encrypted=encrypt("some_access_token"),
        refresh_token_encrypted=encrypt("some_refresh_token"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        external_user_id="spotify_user_999",
        status="active",
    )
    db.add(conn)
    await db.flush()

    response = await verified_authenticated_client.get("/api/streaming/status")

    assert response.status_code == 200
    body = response.json()
    assert len(body["connections"]) == 1
    connection = body["connections"][0]
    assert connection["platform"] == "spotify"
    assert connection["connected"] is True
    assert connection["status"] == "active"
    assert connection["external_user_id"] == "spotify_user_999"


async def test_spotify_status_excludes_pending(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    church_id = await get_verified_user_church_id(db)

    # Insert a pending connection
    conn = StreamingConnection(
        church_id=church_id,
        platform="spotify",
        access_token_encrypted=encrypt("oauth_state_value"),
        refresh_token_encrypted=encrypt("pending"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        external_user_id="pending",
        status="pending",
    )
    db.add(conn)
    await db.flush()

    response = await verified_authenticated_client.get("/api/streaming/status")

    assert response.status_code == 200
    body = response.json()
    assert body["connections"] == []


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------


async def test_spotify_authorize_unauthenticated(client: AsyncClient):
    response = await client.get("/api/streaming/spotify/authorize")
    assert response.status_code == 401


async def test_spotify_authorize_unverified_email(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/streaming/spotify/authorize")
    assert response.status_code == 403
