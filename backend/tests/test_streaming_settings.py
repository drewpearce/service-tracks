"""Tests for per-platform streaming settings + disconnect + reset endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

import respx
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.church_user import ChurchUser
from app.models.playlist import Playlist
from app.models.streaming_connection import StreamingConnection
from app.models.streaming_settings import StreamingSettings
from app.utils.encryption import encrypt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def get_verified_church_id(db: AsyncSession) -> uuid.UUID:
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    return result.scalar_one().church_id


async def csrf_token(client: AsyncClient) -> str:
    """Hit a safe endpoint to ensure the csrf_token cookie is set, then return it."""
    await client.get("/api/health")
    return client.cookies.get("csrf_token", "")


async def add_active_connection(db: AsyncSession, church_id: uuid.UUID, platform: str) -> StreamingConnection:
    conn = StreamingConnection(
        church_id=church_id,
        platform=platform,
        access_token_encrypted=encrypt("access"),
        refresh_token_encrypted=encrypt("refresh"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        external_user_id=f"{platform}_user",
        status="active",
    )
    db.add(conn)
    await db.flush()
    return conn


# ---------------------------------------------------------------------------
# GET /api/streaming/{platform}/settings
# ---------------------------------------------------------------------------


async def test_get_settings_returns_defaults(verified_authenticated_client: AsyncClient):
    response = await verified_authenticated_client.get("/api/streaming/spotify/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["platform"] == "spotify"
    assert body["playlist_mode"] == "shared"
    assert body["playlist_name_template"] == "{church_name} Worship"
    assert body["playlist_description_template"] == "Worship set for {date}"


async def test_get_settings_unknown_platform_404(verified_authenticated_client: AsyncClient):
    response = await verified_authenticated_client.get("/api/streaming/myspace/settings")
    assert response.status_code == 404


async def test_get_settings_unverified(authenticated_client: AsyncClient):
    response = await authenticated_client.get("/api/streaming/spotify/settings")
    assert response.status_code == 403


async def test_get_settings_unauthenticated(client: AsyncClient):
    response = await client.get("/api/streaming/spotify/settings")
    assert response.status_code == 401


async def test_get_settings_isolated_per_platform(verified_authenticated_client: AsyncClient, db: AsyncSession):
    """Updating Spotify settings does not affect YouTube settings."""
    csrf = await csrf_token(verified_authenticated_client)

    await verified_authenticated_client.patch(
        "/api/streaming/spotify/settings",
        json={"playlist_mode": "per_plan", "playlist_name_template": "Spotify-Only"},
        headers={"X-CSRF-Token": csrf},
    )

    yt = await verified_authenticated_client.get("/api/streaming/youtube/settings")
    assert yt.status_code == 200
    body = yt.json()
    assert body["playlist_mode"] == "shared"
    assert body["playlist_name_template"] == "{church_name} Worship"


# ---------------------------------------------------------------------------
# PATCH /api/streaming/{platform}/settings
# ---------------------------------------------------------------------------


async def test_patch_settings_updates_mode(verified_authenticated_client: AsyncClient):
    csrf = await csrf_token(verified_authenticated_client)
    response = await verified_authenticated_client.patch(
        "/api/streaming/spotify/settings",
        json={"playlist_mode": "per_plan"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["playlist_mode"] == "per_plan"
    assert body["playlist_name_template"] == "{church_name} Worship"


async def test_patch_settings_partial_only_changes_provided_fields(verified_authenticated_client: AsyncClient):
    csrf = await csrf_token(verified_authenticated_client)
    await verified_authenticated_client.patch(
        "/api/streaming/spotify/settings",
        json={"playlist_mode": "per_plan"},
        headers={"X-CSRF-Token": csrf},
    )
    response = await verified_authenticated_client.patch(
        "/api/streaming/spotify/settings",
        json={"playlist_name_template": "New Name"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["playlist_mode"] == "per_plan"
    assert body["playlist_name_template"] == "New Name"


async def test_patch_settings_invalid_mode_422(verified_authenticated_client: AsyncClient):
    csrf = await csrf_token(verified_authenticated_client)
    response = await verified_authenticated_client.patch(
        "/api/streaming/spotify/settings",
        json={"playlist_mode": "nonsense"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 422


async def test_patch_settings_unknown_platform_404(verified_authenticated_client: AsyncClient):
    csrf = await csrf_token(verified_authenticated_client)
    response = await verified_authenticated_client.patch(
        "/api/streaming/myspace/settings",
        json={"playlist_mode": "shared"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/streaming/{platform}/reset
# ---------------------------------------------------------------------------


async def test_reset_deletes_playlists_and_resets_settings(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    church_id = await get_verified_church_id(db)
    await add_active_connection(db, church_id, "spotify")
    db.add(
        Playlist(
            church_id=church_id,
            pco_plan_id="__shared__",
            pco_plan_date=datetime.now(timezone.utc).date(),
            platform="spotify",
            external_playlist_id="external_xyz",
            external_playlist_url="https://example/xyz",
            sync_status="synced",
        )
    )
    # Customize settings so we can verify they're reset.
    db.add(
        StreamingSettings(
            church_id=church_id,
            platform="spotify",
            playlist_mode="per_plan",
            playlist_name_template="Custom Name",
            playlist_description_template="Custom Desc",
        )
    )
    await db.flush()

    csrf = await csrf_token(verified_authenticated_client)
    response = await verified_authenticated_client.post(
        "/api/streaming/spotify/reset",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 204

    # Playlist rows for spotify are gone
    playlists = (
        (await db.execute(select(Playlist).where(Playlist.church_id == church_id, Playlist.platform == "spotify")))
        .scalars()
        .all()
    )
    assert playlists == []

    # Settings reset to defaults
    settings_row = (
        await db.execute(
            select(StreamingSettings).where(
                StreamingSettings.church_id == church_id, StreamingSettings.platform == "spotify"
            )
        )
    ).scalar_one()
    assert settings_row.playlist_mode == "shared"
    assert settings_row.playlist_name_template == "{church_name} Worship"
    assert settings_row.playlist_description_template == "Worship set for {date}"


async def test_reset_does_not_touch_other_platform(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)
    await add_active_connection(db, church_id, "spotify")
    await add_active_connection(db, church_id, "youtube")

    db.add(
        Playlist(
            church_id=church_id,
            pco_plan_id="__shared__",
            pco_plan_date=datetime.now(timezone.utc).date(),
            platform="youtube",
            external_playlist_id="yt_playlist",
            external_playlist_url="https://example/yt",
            sync_status="synced",
        )
    )
    await db.flush()

    csrf = await csrf_token(verified_authenticated_client)
    await verified_authenticated_client.post(
        "/api/streaming/spotify/reset",
        headers={"X-CSRF-Token": csrf},
    )

    yt_playlists = (
        (await db.execute(select(Playlist).where(Playlist.church_id == church_id, Playlist.platform == "youtube")))
        .scalars()
        .all()
    )
    assert len(yt_playlists) == 1


async def test_reset_preserves_connection(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)
    await add_active_connection(db, church_id, "spotify")

    csrf = await csrf_token(verified_authenticated_client)
    await verified_authenticated_client.post(
        "/api/streaming/spotify/reset",
        headers={"X-CSRF-Token": csrf},
    )

    conn = (
        await db.execute(
            select(StreamingConnection).where(
                StreamingConnection.church_id == church_id,
                StreamingConnection.platform == "spotify",
            )
        )
    ).scalar_one()
    assert conn.status == "active"


async def test_reset_unknown_platform_404(verified_authenticated_client: AsyncClient):
    csrf = await csrf_token(verified_authenticated_client)
    response = await verified_authenticated_client.post(
        "/api/streaming/myspace/reset",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/streaming/{platform}
# ---------------------------------------------------------------------------


async def test_disconnect_spotify_removes_connection_playlists_and_settings(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    church_id = await get_verified_church_id(db)
    await add_active_connection(db, church_id, "spotify")
    db.add(
        Playlist(
            church_id=church_id,
            pco_plan_id="__shared__",
            pco_plan_date=datetime.now(timezone.utc).date(),
            platform="spotify",
            external_playlist_id="external_xyz",
            external_playlist_url="https://example/xyz",
            sync_status="synced",
        )
    )
    db.add(
        StreamingSettings(
            church_id=church_id,
            platform="spotify",
            playlist_mode="per_plan",
            playlist_name_template="x",
            playlist_description_template="y",
        )
    )
    await db.flush()

    csrf = await csrf_token(verified_authenticated_client)
    response = await verified_authenticated_client.delete(
        "/api/streaming/spotify",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 204

    assert (
        await db.execute(
            select(StreamingConnection).where(
                StreamingConnection.church_id == church_id, StreamingConnection.platform == "spotify"
            )
        )
    ).scalar_one_or_none() is None
    assert (
        await db.execute(select(Playlist).where(Playlist.church_id == church_id, Playlist.platform == "spotify"))
    ).scalars().all() == []
    assert (
        await db.execute(
            select(StreamingSettings).where(
                StreamingSettings.church_id == church_id, StreamingSettings.platform == "spotify"
            )
        )
    ).scalar_one_or_none() is None


@respx.mock
async def test_disconnect_youtube_revokes_token_at_google(verified_authenticated_client: AsyncClient, db: AsyncSession):
    church_id = await get_verified_church_id(db)
    await add_active_connection(db, church_id, "youtube")

    revoke_mock = respx.post("https://oauth2.googleapis.com/revoke").mock(return_value=Response(200))

    csrf = await csrf_token(verified_authenticated_client)
    response = await verified_authenticated_client.delete(
        "/api/streaming/youtube",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 204
    assert revoke_mock.called


@respx.mock
async def test_disconnect_youtube_succeeds_even_when_revoke_fails(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """Local row is removed even if Google's revoke endpoint returns non-200."""
    church_id = await get_verified_church_id(db)
    await add_active_connection(db, church_id, "youtube")

    respx.post("https://oauth2.googleapis.com/revoke").mock(return_value=Response(400))

    csrf = await csrf_token(verified_authenticated_client)
    response = await verified_authenticated_client.delete(
        "/api/streaming/youtube",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 204

    assert (
        await db.execute(
            select(StreamingConnection).where(
                StreamingConnection.church_id == church_id, StreamingConnection.platform == "youtube"
            )
        )
    ).scalar_one_or_none() is None


async def test_disconnect_when_not_connected_404(verified_authenticated_client: AsyncClient):
    csrf = await csrf_token(verified_authenticated_client)
    response = await verified_authenticated_client.delete(
        "/api/streaming/spotify",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 404


async def test_disconnect_unknown_platform_404(verified_authenticated_client: AsyncClient):
    csrf = await csrf_token(verified_authenticated_client)
    response = await verified_authenticated_client.delete(
        "/api/streaming/myspace",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 404


async def test_disconnect_unverified(authenticated_client: AsyncClient):
    await authenticated_client.get("/api/health")
    csrf = authenticated_client.cookies.get("csrf_token", "")
    response = await authenticated_client.delete(
        "/api/streaming/spotify",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 403
