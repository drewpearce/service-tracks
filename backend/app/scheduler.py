"""APScheduler integration for background church sync polling."""

import asyncio
import uuid

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger(__name__)

# Global semaphore: max 10 concurrent sync operations
sync_semaphore = asyncio.Semaphore(10)

# Module-level scheduler instance
scheduler = AsyncIOScheduler()

# Will be set during app startup — the async_session_factory from database.py
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_scheduler(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Store the session factory for use by scheduler jobs."""
    global _session_factory
    _session_factory = session_factory


async def sync_church_with_timeout(church_id: str) -> None:
    """Wrapper that enforces concurrency limit and per-job timeout.

    Args:
        church_id: String UUID of the church (using str for APScheduler
                   serialization safety; converted to UUID internally).
    """
    from app.services.sync_service import sync_church

    church_uuid = uuid.UUID(church_id)

    async with sync_semaphore:
        if _session_factory is None:
            logger.error("scheduler_no_session_factory")
            return

        async with _session_factory() as db:
            try:
                await asyncio.wait_for(
                    sync_church(db, church_uuid, trigger="poll"),
                    timeout=60.0,
                )
                await db.commit()
            except asyncio.TimeoutError:
                logger.error("sync_timeout", church_id=church_id)
                await db.rollback()
            except Exception:
                logger.exception("sync_error", church_id=church_id)
                await db.rollback()


async def start_scheduler(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Query sync-enabled churches and start the scheduler with a job per church.

    NOTE: Scheduled auto-sync is currently disabled pending PCO webhook
    implementation. The scheduler starts but no jobs are registered.
    To re-enable, uncomment the job registration block below.
    """
    init_scheduler(session_factory)

    # --- DISABLED: auto-sync via polling (backlogged for PCO webhook epic) ---
    # async with session_factory() as db:
    #     result = await db.execute(
    #         select(Church).where(Church.sync_enabled == True)  # noqa: E712
    #     )
    #     churches = result.scalars().all()
    # for church in churches:
    #     add_church_sync_job(church.id)
    # -------------------------------------------------------------------------

    scheduler.start()
    logger.info("scheduler_started", job_count=len(scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")


def add_church_sync_job(church_id: uuid.UUID) -> None:
    """Add a sync job for a church. Idempotent — replaces existing job if present."""
    job_id = f"sync_{church_id}"

    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)

    scheduler.add_job(
        sync_church_with_timeout,
        trigger=IntervalTrigger(minutes=5, jitter=120),
        args=[str(church_id)],
        id=job_id,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    logger.info("scheduler_job_added", church_id=str(church_id), job_id=job_id)


def remove_church_sync_job(church_id: uuid.UUID) -> None:
    """Remove a church's sync job. No-op if the job doesn't exist."""
    job_id = f"sync_{church_id}"

    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)
        logger.info("scheduler_job_removed", church_id=str(church_id), job_id=job_id)


def get_scheduler_status() -> dict:
    """Return scheduler health info for the health endpoint."""
    if not scheduler.running:
        return {
            "scheduler": "stopped",
            "scheduler_jobs": 0,
        }

    jobs = scheduler.get_jobs()
    return {
        "scheduler": "running",
        "scheduler_jobs": len(jobs),
    }
