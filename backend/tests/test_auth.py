"""Auth endpoint tests — Epic 3, Task 3.5."""

import hashlib
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import require_verified_email
from app.models.church_user import ChurchUser
from app.models.user_session import UserSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register(client: AsyncClient, email: str = "user@example.com", password: str = "password123"):
    with patch("app.utils.email.send_email", new_callable=AsyncMock):
        response = await client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "church_name": "Test Church"},
        )
    return response


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


async def test_register_success(client):
    response = await _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "user@example.com"
    assert body["user"]["email_verified"] is False
    assert "id" in body["user"]
    assert "church" in body
    assert "session" in response.cookies


async def test_register_duplicate_email(client):
    await _register(client)
    response = await _register(client)
    assert response.status_code == 409


async def test_register_weak_password(client):
    with patch("app.utils.email.send_email", new_callable=AsyncMock):
        response = await client.post(
            "/api/auth/register",
            json={"email": "user@example.com", "password": "short", "church_name": "Test Church"},
        )
    assert response.status_code == 422


async def test_register_invalid_email(client):
    with patch("app.utils.email.send_email", new_callable=AsyncMock):
        response = await client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "password123", "church_name": "Test Church"},
        )
    assert response.status_code == 422


async def test_register_slug_generation(client):
    with patch("app.utils.email.send_email", new_callable=AsyncMock):
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "password": "password123",
                "church_name": "Grace Community Church",
            },
        )
    assert response.status_code == 201
    slug = response.json()["church"]["slug"]
    assert "grace-community-church" in slug


async def test_register_sends_verification_email(client):
    with patch("app.utils.email.send_email", new_callable=AsyncMock) as mock_email:
        response = await client.post(
            "/api/auth/register",
            json={"email": "user@example.com", "password": "password123", "church_name": "Test Church"},
        )
    assert response.status_code == 201
    mock_email.assert_called_once()
    call_args = mock_email.call_args
    assert call_args[0][0] == "user@example.com"  # to
    assert "Verify" in call_args[0][1]  # subject


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------


async def test_login_success(client):
    await _register(client)
    response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert "session" in response.cookies


async def test_login_wrong_password(client):
    await _register(client)
    response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


async def test_login_nonexistent_email(client):
    response = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


# ---------------------------------------------------------------------------
# Logout tests
# ---------------------------------------------------------------------------


async def test_logout_clears_session(client):
    await _register(client)
    # The session cookie is set automatically on the client after registration
    logout_response = await client.post(
        "/api/auth/logout",
        headers={"x-csrf-token": client.cookies.get("csrf_token", "")},
    )
    assert logout_response.status_code == 204

    me_response = await client.get("/api/auth/me")
    assert me_response.status_code == 401


# ---------------------------------------------------------------------------
# Session middleware tests
# ---------------------------------------------------------------------------


async def test_me_authenticated(client):
    await _register(client)
    response = await client.get("/api/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "user@example.com"
    assert "church" in body


async def test_me_unauthenticated(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_expired_session(client, db: AsyncSession):
    await _register(client)

    # Expire the session directly in the DB
    session_token = client.cookies.get("session")
    result = await db.execute(select(UserSession).where(UserSession.id == session_token))
    session_row = result.scalar_one()
    session_row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.flush()

    response = await client.get("/api/auth/me")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# CSRF tests
# ---------------------------------------------------------------------------


async def test_csrf_required_on_protected_post(client):
    await _register(client)
    # POST /logout without X-CSRF-Token header should return 403
    response = await client.post("/api/auth/logout")
    assert response.status_code == 403


async def test_csrf_exempt_endpoints(client):
    # POST /login without CSRF token should NOT return 403 (returns 401 for bad creds)
    response = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert response.status_code != 403
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Email verification tests
# ---------------------------------------------------------------------------


async def test_verify_email_success(client, db: AsyncSession):
    await _register(client)

    # Read verification token from DB
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == "user@example.com"))
    user = result.scalar_one()
    token = user.email_verification_token
    assert token is not None

    response = await client.post("/api/auth/verify-email", json={"token": token})
    assert response.status_code == 200
    assert response.json()["email_verified"] is True

    # Confirm DB state — endpoint modified the same session object in-memory;
    # flush to ensure writes are visible then re-query.
    await db.flush()
    result2 = await db.execute(select(ChurchUser).where(ChurchUser.email == "user@example.com"))
    user2 = result2.scalar_one()
    assert user2.email_verified is True
    assert user2.email_verification_token is None


async def test_verify_email_expired_token(client, db: AsyncSession):
    await _register(client)

    result = await db.execute(select(ChurchUser).where(ChurchUser.email == "user@example.com"))
    user = result.scalar_one()
    user.email_verification_sent_at = datetime.now(timezone.utc) - timedelta(hours=25)
    await db.flush()

    response = await client.post("/api/auth/verify-email", json={"token": user.email_verification_token})
    assert response.status_code == 400


async def test_verify_email_invalid_token(client):
    response = await client.post("/api/auth/verify-email", json={"token": "invalidtoken"})
    assert response.status_code == 400


async def test_resend_verification(client, db: AsyncSession):
    await _register(client)

    # Clear the cooldown left by registration's verification email
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == "user@example.com"))
    user = result.scalar_one()
    user.email_verification_sent_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    await db.flush()

    with patch("app.utils.email.send_email", new_callable=AsyncMock):
        response = await client.post(
            "/api/auth/resend-verification",
            headers={"x-csrf-token": client.cookies.get("csrf_token", "")},
        )
    assert response.status_code == 200


async def test_resend_verification_rate_limit(client, db: AsyncSession):
    await _register(client)

    # Clear the cooldown so first resend is accepted
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == "user@example.com"))
    user = result.scalar_one()
    user.email_verification_sent_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    await db.flush()

    csrf = client.cookies.get("csrf_token", "")
    with patch("app.utils.email.send_email", new_callable=AsyncMock):
        first = await client.post(
            "/api/auth/resend-verification",
            headers={"x-csrf-token": csrf},
        )
    assert first.status_code == 200

    # Second request within cooldown should be 429
    with patch("app.utils.email.send_email", new_callable=AsyncMock):
        second = await client.post(
            "/api/auth/resend-verification",
            headers={"x-csrf-token": csrf},
        )
    assert second.status_code == 429


# ---------------------------------------------------------------------------
# Forgot/reset password tests
# ---------------------------------------------------------------------------


async def test_forgot_password_existing_email(client, db: AsyncSession):
    await _register(client)
    with patch("app.utils.email.send_email", new_callable=AsyncMock):
        response = await client.post(
            "/api/auth/forgot-password",
            json={"email": "user@example.com"},
        )
    assert response.status_code == 200

    result = await db.execute(select(ChurchUser).where(ChurchUser.email == "user@example.com"))
    user = result.scalar_one()
    assert user.password_reset_token is not None


async def test_forgot_password_nonexistent_email(client):
    response = await client.post(
        "/api/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 200


async def test_reset_password_success(client):
    await _register(client)

    with patch("app.utils.email.send_email", new_callable=AsyncMock) as mock_email:
        await client.post(
            "/api/auth/forgot-password",
            json={"email": "user@example.com"},
        )

    # Extract raw token from the email link
    call_args = mock_email.call_args
    html_body = call_args[0][2]
    match = re.search(r"token=([A-Za-z0-9_\-]+)", html_body)
    assert match, f"Could not find token in email body: {html_body}"
    raw_token = match.group(1)

    response = await client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "newpassword456"},
    )
    assert response.status_code == 200

    # Login with new password should work
    login_new = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "newpassword456"},
    )
    assert login_new.status_code == 200

    # Login with old password should fail
    login_old = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert login_old.status_code == 401


async def test_reset_password_expired_token(client, db: AsyncSession):
    await _register(client)

    with patch("app.utils.email.send_email", new_callable=AsyncMock) as mock_email:
        await client.post(
            "/api/auth/forgot-password",
            json={"email": "user@example.com"},
        )

    call_args = mock_email.call_args
    html_body = call_args[0][2]
    match = re.search(r"token=([A-Za-z0-9_\-]+)", html_body)
    assert match
    raw_token = match.group(1)

    # Expire the token
    hashed = hashlib.sha256(raw_token.encode()).hexdigest()
    result = await db.execute(select(ChurchUser).where(ChurchUser.password_reset_token == hashed))
    user = result.scalar_one()
    user.password_reset_sent_at = datetime.now(timezone.utc) - timedelta(hours=2)
    await db.flush()

    response = await client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "newpassword456"},
    )
    assert response.status_code == 400


async def test_reset_password_invalid_token(client):
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": "randomtoken", "new_password": "newpassword456"},
    )
    assert response.status_code == 400


async def test_reset_password_invalidates_sessions(client):
    await _register(client)
    old_session_token = client.cookies.get("session")

    with patch("app.utils.email.send_email", new_callable=AsyncMock) as mock_email:
        await client.post(
            "/api/auth/forgot-password",
            json={"email": "user@example.com"},
        )

    call_args = mock_email.call_args
    html_body = call_args[0][2]
    match = re.search(r"token=([A-Za-z0-9_\-]+)", html_body)
    assert match
    raw_token = match.group(1)

    await client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "newpassword456"},
    )

    # Manually set the old session cookie on client and check /me returns 401
    client.cookies.set("session", old_session_token)
    me_response = await client.get("/api/auth/me")
    assert me_response.status_code == 401


# ---------------------------------------------------------------------------
# Rate limiting test
# ---------------------------------------------------------------------------


async def test_login_rate_limit(client):
    responses = []
    for _ in range(11):
        r = await client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        responses.append(r.status_code)
    assert 429 in responses


# ---------------------------------------------------------------------------
# Email-verified dependency test
# ---------------------------------------------------------------------------


async def test_require_verified_email_blocks_unverified(client):
    await _register(client)
    me_resp = await client.get("/api/auth/me")
    user_data = me_resp.json()["user"]
    assert user_data["email_verified"] is False

    # Create a mock request with unverified user state
    mock_request = MagicMock()
    mock_request.state.current_user = MagicMock(email_verified=False)

    with pytest.raises(HTTPException) as exc_info:
        await require_verified_email(mock_request)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "email_not_verified"
