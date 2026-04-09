"""Scheduler unit tests — Epic 7.

Tests for scheduler management functions. These do NOT start the real scheduler
or wait for jobs to fire. Only test_start_scheduler_loads_churches uses the real DB.
asyncio_mode = "auto" (set in pyproject.toml) makes all async test functions run automatically.
"""

import uuid
from unittest.mock import patch

import pytest
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.church import Church
from app.scheduler import (
    add_church_sync_job,
    get_scheduler_status,
    remove_church_sync_job,
    scheduler,
    start_scheduler,
    stop_scheduler,
)

# ---------------------------------------------------------------------------
# Autouse fixture: ensure scheduler is stopped and jobs cleared after each test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def cleanup_scheduler():
    """Ensure scheduler is stopped and jobs are cleared after each test."""
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Test 1: add_church_sync_job — job added to scheduler
# ---------------------------------------------------------------------------


async def test_add_church_sync_job():
    scheduler.start()
    church_id = uuid.uuid4()
    add_church_sync_job(church_id)

    job = scheduler.get_job(f"sync_{church_id}")
    assert job is not None
    assert isinstance(job.trigger, IntervalTrigger)


# ---------------------------------------------------------------------------
# Test 2: add_church_sync_job idempotent — adding same church twice replaces job
# ---------------------------------------------------------------------------


async def test_add_church_sync_job_idempotent():
    scheduler.start()
    church_id = uuid.uuid4()
    add_church_sync_job(church_id)
    add_church_sync_job(church_id)

    # Only 1 job should exist with that ID
    jobs = [j for j in scheduler.get_jobs() if j.id == f"sync_{church_id}"]
    assert len(jobs) == 1


# ---------------------------------------------------------------------------
# Test 3: remove_church_sync_job — job removed
# ---------------------------------------------------------------------------


async def test_remove_church_sync_job():
    scheduler.start()
    church_id = uuid.uuid4()
    add_church_sync_job(church_id)

    remove_church_sync_job(church_id)

    job = scheduler.get_job(f"sync_{church_id}")
    assert job is None


# ---------------------------------------------------------------------------
# Test 4: remove_church_sync_job no-op when job doesn't exist
# ---------------------------------------------------------------------------


async def test_remove_church_sync_job_noop():
    scheduler.start()
    church_id = uuid.uuid4()
    # Should not raise
    remove_church_sync_job(church_id)


# ---------------------------------------------------------------------------
# Test 5: get_scheduler_status when running
# ---------------------------------------------------------------------------


async def test_get_scheduler_status_running():
    scheduler.start()
    church_id = uuid.uuid4()
    add_church_sync_job(church_id)

    status = get_scheduler_status()
    assert status["scheduler"] == "running"
    assert status["scheduler_jobs"] == 1


# ---------------------------------------------------------------------------
# Test 6: get_scheduler_status when stopped
# ---------------------------------------------------------------------------


def test_get_scheduler_status_stopped():
    # Scheduler should not be running (cleanup_scheduler fixture ensures this)
    status = get_scheduler_status()
    assert status["scheduler"] == "stopped"
    assert status["scheduler_jobs"] == 0


# ---------------------------------------------------------------------------
# Test 7: start_scheduler loads sync-enabled churches from DB
# ---------------------------------------------------------------------------


async def test_start_scheduler_loads_churches(db_session):
    """Scheduled auto-sync is currently disabled (backlogged for PCO webhook epic).

    start_scheduler should start the scheduler with no jobs registered,
    regardless of how many sync-enabled churches exist.
    """
    db, connection = db_session

    church1 = Church(name="Church 1", slug="church-sync-1", sync_enabled=True)
    church2 = Church(name="Church 2", slug="church-sync-2", sync_enabled=True)
    church3 = Church(name="Church 3", slug="church-sync-3", sync_enabled=False)
    db.add(church1)
    db.add(church2)
    db.add(church3)
    await db.flush()

    test_session_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)

    await start_scheduler(test_session_factory)

    try:
        jobs = scheduler.get_jobs()
        sync_jobs = [j for j in jobs if j.id.startswith("sync_")]
        assert len(sync_jobs) == 0
    finally:
        stop_scheduler()


# ---------------------------------------------------------------------------
# Test 8: health endpoint includes scheduler status
# ---------------------------------------------------------------------------


async def test_health_includes_scheduler(client):
    with patch(
        "app.routers.health.get_scheduler_status",
        return_value={
            "scheduler": "running",
            "scheduler_jobs": 5,
        },
    ):
        response = await client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["scheduler"] == "running"
    assert body["scheduler_jobs"] == 5


# ---------------------------------------------------------------------------
# Test 9: health endpoint returns 503 when scheduler is stopped
# ---------------------------------------------------------------------------


async def test_health_endpoint_503_when_scheduler_stopped(client):
    with patch(
        "app.routers.health.get_scheduler_status",
        return_value={
            "scheduler": "stopped",
            "scheduler_jobs": 0,
        },
    ):
        response = await client.get("/api/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
