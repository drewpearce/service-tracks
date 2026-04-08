"""PCO service layer — credential lookup, decryption, and PcoClient instantiation.

Used by the sync engine (Epic 7) and plan-fetching endpoints.
"""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.pco_client import PcoApiError, PcoClient
from app.models.church import Church
from app.models.pco_connection import PcoConnection
from app.schemas.pco import Plan, PlanSong
from app.utils.encryption import decrypt

logger = structlog.get_logger(__name__)


async def get_pco_client(db: AsyncSession, church_id: uuid.UUID) -> PcoClient:
    """Return a PcoClient instantiated with decrypted credentials for the given church.

    Raises:
        ValueError: "pco_not_connected" if no connection row exists.
        ValueError: "pco_connection_inactive" if the connection status is not "active".
    """
    result = await db.execute(select(PcoConnection).where(PcoConnection.church_id == church_id))
    conn = result.scalar_one_or_none()

    if conn is None:
        raise ValueError("pco_not_connected")
    if conn.status != "active":
        raise ValueError("pco_connection_inactive")

    app_id = decrypt(conn.app_id_encrypted)
    secret = decrypt(conn.secret_encrypted)
    return PcoClient(app_id, secret)


async def get_upcoming_plans_for_church(db: AsyncSession, church_id: uuid.UUID) -> list[Plan]:
    """Fetch upcoming plans for a church using its stored PCO credentials.

    Returns an empty list if no service type is configured.
    Catches and re-raises PcoApiError subclasses after logging.
    """
    # Get the service type ID from the church record
    church_result = await db.execute(select(Church).where(Church.id == church_id))
    church = church_result.scalar_one_or_none()
    if church is None or church.pco_service_type_id is None:
        return []

    client = await get_pco_client(db, church_id)

    try:
        plans = await client.get_upcoming_plans(church.pco_service_type_id)
    except PcoApiError:
        logger.exception("Failed to fetch upcoming plans from PCO", church_id=str(church_id))
        raise

    # Update last_successful_call_at
    conn_result = await db.execute(select(PcoConnection).where(PcoConnection.church_id == church_id))
    conn = conn_result.scalar_one()
    conn.last_successful_call_at = datetime.now(timezone.utc)
    await db.flush()

    return plans


async def get_plan_for_church(db: AsyncSession, church_id: uuid.UUID, plan_id: str) -> Plan | None:
    """Fetch metadata (title, date) for a single PCO plan.

    Returns None if no service type is configured or the plan is not found.
    """
    church_result = await db.execute(select(Church).where(Church.id == church_id))
    church = church_result.scalar_one_or_none()
    if church is None or church.pco_service_type_id is None:
        return None

    client = await get_pco_client(db, church_id)
    try:
        return await client.get_plan(church.pco_service_type_id, plan_id)
    except PcoApiError:
        logger.exception("Failed to fetch plan from PCO", church_id=str(church_id), plan_id=plan_id)
        return None


async def get_plan_songs_for_church(db: AsyncSession, church_id: uuid.UUID, plan_id: str) -> list[PlanSong]:
    """Fetch songs for a specific plan using the church's stored PCO credentials.

    Returns an empty list if no service type is configured.
    Catches and re-raises PcoApiError subclasses after logging.
    """
    church_result = await db.execute(select(Church).where(Church.id == church_id))
    church = church_result.scalar_one_or_none()
    if church is None or church.pco_service_type_id is None:
        return []

    client = await get_pco_client(db, church_id)

    try:
        songs = await client.get_plan_songs(church.pco_service_type_id, plan_id)
    except PcoApiError:
        logger.exception("Failed to fetch plan songs from PCO", church_id=str(church_id), plan_id=plan_id)
        raise

    # Update last_successful_call_at
    conn_result = await db.execute(select(PcoConnection).where(PcoConnection.church_id == church_id))
    conn = conn_result.scalar_one()
    conn.last_successful_call_at = datetime.now(timezone.utc)
    await db.flush()

    return songs
