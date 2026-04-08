"""Tests for GET /api/settings and PATCH /api/settings."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# GET /api/settings
# ---------------------------------------------------------------------------


async def test_get_settings_unauthenticated(client: AsyncClient):
    """Unauthenticated request returns 401."""
    await client.get("/api/health")
    response = await client.get("/api/settings")
    assert response.status_code == 401


async def test_get_settings_unverified(authenticated_client: AsyncClient):
    """Unverified user returns 403."""
    response = await authenticated_client.get("/api/settings")
    assert response.status_code == 403


async def test_get_settings_returns_defaults(verified_authenticated_client: AsyncClient):
    """GET /api/settings returns the default values for a freshly registered church."""
    response = await verified_authenticated_client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["playlist_mode"] == "shared"
    assert body["playlist_name_template"] == "{church_name} Worship"
    assert body["playlist_description_template"] == "Worship set for {date}"


# ---------------------------------------------------------------------------
# PATCH /api/settings
# ---------------------------------------------------------------------------


async def test_patch_settings_unauthenticated(client: AsyncClient):
    """Unauthenticated PATCH returns 403 (CSRF) or 401 (auth); in either case not 200."""
    # The CSRF middleware runs before auth, so an empty token yields 403.
    # The important thing is the request is rejected.
    await client.get("/api/health")
    csrf_token = client.cookies.get("csrf_token", "")
    response = await client.patch(
        "/api/settings",
        json={"playlist_mode": "per_plan"},
        headers={"X-CSRF-Token": csrf_token},
    )
    # Unauthenticated — auth middleware should reject with 401
    assert response.status_code == 401


async def test_patch_settings_updates_playlist_mode(
    verified_authenticated_client: AsyncClient, db: AsyncSession
):
    """PATCH updates playlist_mode and returns the new value."""
    csrf = ""
    # Get a CSRF token first
    await verified_authenticated_client.get("/api/health")

    cookies = verified_authenticated_client.cookies
    csrf = cookies.get("csrf_token", "")

    response = await verified_authenticated_client.patch(
        "/api/settings",
        json={"playlist_mode": "per_plan"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["playlist_mode"] == "per_plan"
    # Other fields unchanged
    assert body["playlist_name_template"] == "{church_name} Worship"
    assert body["playlist_description_template"] == "Worship set for {date}"


async def test_patch_settings_updates_name_template(
    verified_authenticated_client: AsyncClient,
):
    """PATCH updates playlist_name_template."""
    await verified_authenticated_client.get("/api/health")
    csrf = verified_authenticated_client.cookies.get("csrf_token", "")

    response = await verified_authenticated_client.patch(
        "/api/settings",
        json={"playlist_name_template": "{church_name} — {date}"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["playlist_name_template"] == "{church_name} — {date}"
    # Other fields unchanged
    assert body["playlist_mode"] == "shared"


async def test_patch_settings_updates_description_template(
    verified_authenticated_client: AsyncClient,
):
    """PATCH updates playlist_description_template."""
    await verified_authenticated_client.get("/api/health")
    csrf = verified_authenticated_client.cookies.get("csrf_token", "")

    response = await verified_authenticated_client.patch(
        "/api/settings",
        json={"playlist_description_template": "Sunday worship — {date_iso}"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["playlist_description_template"] == "Sunday worship — {date_iso}"


async def test_patch_settings_invalid_mode_422(
    verified_authenticated_client: AsyncClient,
):
    """PATCH with invalid playlist_mode returns 422."""
    await verified_authenticated_client.get("/api/health")
    csrf = verified_authenticated_client.cookies.get("csrf_token", "")

    response = await verified_authenticated_client.patch(
        "/api/settings",
        json={"playlist_mode": "invalid_mode"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 422


async def test_patch_settings_partial_update_only_changes_provided_fields(
    verified_authenticated_client: AsyncClient,
):
    """PATCH only updates the fields provided; omitted fields stay the same."""
    await verified_authenticated_client.get("/api/health")
    csrf = verified_authenticated_client.cookies.get("csrf_token", "")

    # First change mode to per_plan
    await verified_authenticated_client.patch(
        "/api/settings",
        json={"playlist_mode": "per_plan"},
        headers={"X-CSRF-Token": csrf},
    )

    # Then update only name_template — mode should still be per_plan
    response = await verified_authenticated_client.patch(
        "/api/settings",
        json={"playlist_name_template": "New Name"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["playlist_mode"] == "per_plan"
    assert body["playlist_name_template"] == "New Name"
