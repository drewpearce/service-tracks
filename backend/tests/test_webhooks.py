"""Webhook endpoint integration tests — Epic 8.

Tests use real PostgreSQL (service_tracks_test DB) with per-test transaction rollback.
asyncio_mode = "auto" (set in pyproject.toml) makes all async test functions run automatically.

Two-layer testing approach:
- Router-level tests: mock process_pco_webhook to verify 200/403 responses.
- Service-level tests: call process_pco_webhook directly; mock sync_plan.
"""

import hashlib
import hmac
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from app.models.church import Church
from app.models.pco_connection import PcoConnection
from app.services.webhook_service import process_pco_webhook
from app.utils.encryption import encrypt

TEST_SECRET = "test-webhook-secret"
PCO_WEBHOOK_PATH = "/api/webhooks/pco"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def set_webhook_secret(monkeypatch):
    """Ensure PCO_WEBHOOK_SECRET is set to a known value for all tests."""
    monkeypatch.setattr("app.config.settings.PCO_WEBHOOK_SECRET", TEST_SECRET)
    # Also patch the router's imported settings reference
    monkeypatch.setattr("app.routers.webhooks.settings.PCO_WEBHOOK_SECRET", TEST_SECRET)


def _make_signature(body: bytes, secret: str = TEST_SECRET) -> str:
    """Compute the expected HMAC-SHA256 signature for a payload."""
    return hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()


def _build_payload(organization_id: str = "org123", plan_id: str = "plan456") -> dict:
    """Build a minimal PCO webhook payload."""
    return {
        "meta": {
            "event": "plan.updated",
            "organization_id": organization_id,
        },
        "data": [
            {
                "type": "Plan",
                "id": plan_id,
                "relationships": {},
            }
        ],
    }


# ---------------------------------------------------------------------------
# Router-level tests (mock process_pco_webhook)
# ---------------------------------------------------------------------------


async def test_valid_webhook_returns_200(client: AsyncClient):
    """Valid HMAC signature returns 200 and dispatches background task."""
    payload = _build_payload()
    body = json.dumps(payload).encode()
    signature = _make_signature(body)

    with patch(
        "app.routers.webhooks.process_pco_webhook",
        new_callable=AsyncMock,
    ):
        response = await client.post(
            PCO_WEBHOOK_PATH,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-PCO-Webhooks-Authenticity": signature,
            },
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}


async def test_invalid_hmac_returns_403(client: AsyncClient):
    """Wrong HMAC signature returns 403."""
    payload = _build_payload()
    body = json.dumps(payload).encode()

    response = await client.post(
        PCO_WEBHOOK_PATH,
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-PCO-Webhooks-Authenticity": "wrong-signature",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"error": "invalid_signature"}


async def test_missing_signature_header_returns_403(client: AsyncClient):
    """Missing X-PCO-Webhooks-Authenticity header returns 403."""
    payload = _build_payload()
    body = json.dumps(payload).encode()

    response = await client.post(
        PCO_WEBHOOK_PATH,
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 403
    assert response.json() == {"error": "invalid_signature"}


async def test_valid_webhook_no_matching_church_returns_200(client: AsyncClient):
    """Valid signature with unknown organization returns 200 (webhook accepted, no sync)."""
    payload = _build_payload(organization_id="unknown-org-999")
    body = json.dumps(payload).encode()
    signature = _make_signature(body)

    with patch(
        "app.routers.webhooks.process_pco_webhook",
        new_callable=AsyncMock,
    ) as mock_process:
        response = await client.post(
            PCO_WEBHOOK_PATH,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-PCO-Webhooks-Authenticity": signature,
            },
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}
    # The background task was dispatched (process_pco_webhook was called)
    mock_process.assert_called_once()


# ---------------------------------------------------------------------------
# Service-level tests (call process_pco_webhook directly)
# ---------------------------------------------------------------------------


async def test_process_pco_webhook_triggers_sync(db_session: tuple[AsyncSession, AsyncConnection]):
    """process_pco_webhook calls sync_plan when church and plan are found."""
    db, connection = db_session

    # Build a session factory bound to the same test connection (shares the transaction)
    test_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)

    # Create a church and PcoConnection with a known app_id
    org_id = "test-org-" + str(uuid.uuid4())
    plan_id = "plan-" + str(uuid.uuid4())
    slug = "webhook-test-" + str(uuid.uuid4())[:8]

    church = Church(name="Webhook Test Church", slug=slug)
    db.add(church)
    await db.flush()

    pco_conn = PcoConnection(
        church_id=church.id,
        auth_method="api_key",
        app_id_encrypted=encrypt(org_id),
        secret_encrypted=encrypt("some-secret"),
        status="active",
    )
    db.add(pco_conn)
    await db.flush()

    payload = {
        "meta": {
            "event": "plan.updated",
            "organization_id": org_id,
        },
        "data": [
            {
                "type": "Plan",
                "id": plan_id,
                "relationships": {},
            }
        ],
    }
    raw_body = json.dumps(payload).encode()

    with patch(
        "app.services.webhook_service.sync_plan",
        new_callable=AsyncMock,
    ) as mock_sync:
        await process_pco_webhook(raw_body, test_factory)

    mock_sync.assert_called_once()
    call_kwargs = mock_sync.call_args
    # sync_plan(db, church_id, plan_id, trigger="webhook")
    assert call_kwargs.args[1] == church.id
    assert call_kwargs.args[2] == plan_id
    assert call_kwargs.kwargs.get("trigger") == "webhook"


async def test_process_pco_webhook_no_org_id_skips_sync():
    """process_pco_webhook logs warning and returns early if no organization_id."""
    payload = {"meta": {"event": "plan.updated"}, "data": []}
    raw_body = json.dumps(payload).encode()

    mock_factory = MagicMock()

    with patch("app.services.webhook_service.sync_plan", new_callable=AsyncMock) as mock_sync:
        await process_pco_webhook(raw_body, mock_factory)

    mock_sync.assert_not_called()
    # Factory was never used (no DB access needed when org_id is missing)
    mock_factory.assert_not_called()


async def test_process_pco_webhook_invalid_json_skips_sync():
    """process_pco_webhook handles invalid JSON without raising."""
    raw_body = b"not-valid-json"
    mock_factory = MagicMock()

    with patch("app.services.webhook_service.sync_plan", new_callable=AsyncMock) as mock_sync:
        await process_pco_webhook(raw_body, mock_factory)

    mock_sync.assert_not_called()


async def test_process_pco_webhook_no_matching_church_skips_sync(
    db_session: tuple[AsyncSession, AsyncConnection],
):
    """process_pco_webhook skips sync when no church matches the organization_id."""
    db, connection = db_session
    test_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)

    payload = {
        "meta": {
            "event": "plan.updated",
            "organization_id": "nonexistent-org-" + str(uuid.uuid4()),
        },
        "data": [{"type": "Plan", "id": "plan-123", "relationships": {}}],
    }
    raw_body = json.dumps(payload).encode()

    with patch("app.services.webhook_service.sync_plan", new_callable=AsyncMock) as mock_sync:
        await process_pco_webhook(raw_body, test_factory)

    mock_sync.assert_not_called()
