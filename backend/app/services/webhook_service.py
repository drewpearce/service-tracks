import json
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.pco_connection import PcoConnection
from app.services.sync_service import sync_plan
from app.utils.encryption import decrypt

logger = structlog.get_logger(__name__)


async def process_pco_webhook(
    raw_body: bytes,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Parse a validated PCO webhook payload and trigger sync if applicable.

    This runs as a background task (asyncio.create_task) with its own DB session,
    outside the HTTP request lifecycle. Same pattern as scheduler.py.
    """
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.error("pco_webhook_invalid_json")
        return

    event_name = _extract_event_name(payload)
    organization_id = _extract_organization_id(payload)

    logger.info(
        "pco_webhook_processing",
        event_name=event_name,
        organization_id=organization_id,
    )

    if not organization_id:
        logger.warning("pco_webhook_no_organization_id")
        return

    # Find the church that owns this webhook
    async with session_factory() as db:
        try:
            church_id = await _find_church_by_pco_org(db, organization_id)
            if church_id is None:
                logger.warning(
                    "pco_webhook_no_matching_church",
                    organization_id=organization_id,
                )
                return

            # Extract plan_id from the payload if available
            plan_id = _extract_plan_id(payload)
            if not plan_id:
                logger.warning("pco_webhook_no_plan_id", event_name=event_name)
                return

            # Trigger sync
            await sync_plan(
                db,
                church_id,
                plan_id,
                trigger="webhook",
            )
            await db.commit()
            logger.info(
                "pco_webhook_sync_complete",
                church_id=str(church_id),
                plan_id=plan_id,
            )
        except Exception:
            logger.exception("pco_webhook_processing_error")
            await db.rollback()


def _extract_event_name(payload: dict) -> str | None:
    """Extract the event name from a PCO webhook payload."""
    meta = payload.get("meta", {})
    return meta.get("event") or payload.get("event")


def _extract_organization_id(payload: dict) -> str | None:
    """Extract the PCO organization/application ID from the webhook payload.

    PCO webhooks include organization info. The exact field depends on the
    webhook version. We check multiple locations for robustness.
    """
    # Check meta.organization_id
    meta = payload.get("meta", {})
    org_id = meta.get("organization_id")
    if org_id:
        return str(org_id)

    # Check top-level organization
    org = payload.get("organization", {})
    if isinstance(org, dict) and org.get("id"):
        return str(org["id"])

    # Check data[0].relationships.organization if present
    data = payload.get("data", [])
    if isinstance(data, list) and data:
        rels = data[0].get("relationships", {})
        org_rel = rels.get("organization", {})
        org_data = org_rel.get("data", {})
        if isinstance(org_data, dict) and org_data.get("id"):
            return str(org_data["id"])

    return None


def _extract_plan_id(payload: dict) -> str | None:
    """Extract the plan ID from a PCO webhook payload.

    For plan_item events, the plan_id is in the item's relationships.
    """
    data = payload.get("data", [])
    if isinstance(data, list) and data:
        item = data[0]
        # Direct plan reference in relationships
        rels = item.get("relationships", {})
        plan_rel = rels.get("plan", {})
        plan_data = plan_rel.get("data", {})
        if isinstance(plan_data, dict) and plan_data.get("id"):
            return str(plan_data["id"])

        # The item itself might be a plan
        if item.get("type") == "Plan" and item.get("id"):
            return str(item["id"])

    return None


async def _find_church_by_pco_org(
    db: AsyncSession,
    organization_id: str,
) -> uuid.UUID | None:
    """Find the church_id whose PcoConnection matches the given organization_id.

    INTERIM APPROACH: Loads all active PcoConnections and decrypts app_id to compare.
    This is O(n) in the number of churches but acceptable for early-stage usage.

    FUTURE OPTIMIZATION: Add a `pco_organization_id` (plaintext or hashed) column
    to pco_connection for direct SQL lookup. This avoids loading and decrypting all rows.
    """
    result = await db.execute(
        select(PcoConnection).where(PcoConnection.status == "active")
    )
    connections = result.scalars().all()

    for conn in connections:
        if conn.app_id_encrypted:
            try:
                decrypted_app_id = decrypt(conn.app_id_encrypted)
                if decrypted_app_id == organization_id:
                    return conn.church_id
            except Exception:
                logger.warning(
                    "pco_webhook_decrypt_error",
                    connection_id=str(conn.id),
                )
                continue

    return None
