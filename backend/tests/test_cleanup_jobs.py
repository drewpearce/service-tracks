"""Tests for daily cleanup jobs (search cache + expired sessions)."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.church import Church
from app.models.church_user import ChurchUser
from app.models.search_cache import SearchCache
from app.models.user_session import UserSession
from app.scheduler import (
    cleanup_expired_sessions,
    cleanup_stale_search_cache,
    init_scheduler,
    scheduler,
    start_scheduler,
    stop_scheduler,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_church_and_user(db: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a church + user for session FK constraints. Returns (church_id, user_id)."""
    church = Church(name="Cleanup Test Church", slug=f"cleanup-{uuid.uuid4().hex[:8]}")
    db.add(church)
    await db.flush()

    user = ChurchUser(
        email=f"cleanup-{uuid.uuid4().hex[:8]}@test.com",
        password_hash="fakehash",
        church_id=church.id,
    )
    db.add(user)
    await db.flush()
    return church.id, user.id


# ---------------------------------------------------------------------------
# cleanup_expired_sessions
# ---------------------------------------------------------------------------


async def test_cleanup_deletes_expired_sessions(db_session):
    db, connection = db_session
    church_id, user_id = await _create_church_and_user(db)

    now = datetime.now(timezone.utc)

    # Expired session (yesterday)
    expired = UserSession(
        id="expired-session",
        user_id=user_id,
        church_id=church_id,
        expires_at=now - timedelta(days=1),
    )
    # Valid session (tomorrow)
    valid = UserSession(
        id="valid-session",
        user_id=user_id,
        church_id=church_id,
        expires_at=now + timedelta(days=1),
    )
    db.add_all([expired, valid])
    await db.flush()

    session_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)
    init_scheduler(session_factory)

    await cleanup_expired_sessions()

    result = await db.execute(select(UserSession).where(UserSession.user_id == user_id))
    remaining = result.scalars().all()
    assert len(remaining) == 1
    assert remaining[0].id == "valid-session"


async def test_cleanup_sessions_noop_when_none_expired(db_session):
    db, connection = db_session
    church_id, user_id = await _create_church_and_user(db)

    now = datetime.now(timezone.utc)
    valid = UserSession(
        id="still-valid",
        user_id=user_id,
        church_id=church_id,
        expires_at=now + timedelta(days=7),
    )
    db.add(valid)
    await db.flush()

    session_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)
    init_scheduler(session_factory)

    await cleanup_expired_sessions()

    result = await db.execute(select(UserSession).where(UserSession.user_id == user_id))
    remaining = result.scalars().all()
    assert len(remaining) == 1


# ---------------------------------------------------------------------------
# cleanup_stale_search_cache
# ---------------------------------------------------------------------------


async def test_cleanup_deletes_stale_cache(db_session):
    db, connection = db_session

    now = datetime.now(timezone.utc)

    # Stale entry (10 days old)
    stale = SearchCache(
        platform="spotify",
        query="old search",
        results={"tracks": []},
        created_at=now - timedelta(days=10),
    )
    # Fresh entry (1 day old)
    fresh = SearchCache(
        platform="spotify",
        query="new search",
        results={"tracks": []},
        created_at=now - timedelta(days=1),
    )
    db.add_all([stale, fresh])
    await db.flush()

    session_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)
    init_scheduler(session_factory)

    await cleanup_stale_search_cache()

    result = await db.execute(select(SearchCache))
    remaining = result.scalars().all()
    assert len(remaining) == 1
    assert remaining[0].query == "new search"


async def test_cleanup_cache_noop_when_all_fresh(db_session):
    db, connection = db_session

    fresh = SearchCache(
        platform="youtube",
        query="recent search",
        results={"tracks": []},
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db.add(fresh)
    await db.flush()

    session_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)
    init_scheduler(session_factory)

    await cleanup_stale_search_cache()

    result = await db.execute(select(SearchCache))
    remaining = result.scalars().all()
    assert len(remaining) == 1


# ---------------------------------------------------------------------------
# start_scheduler registers cleanup jobs
# ---------------------------------------------------------------------------


async def test_start_scheduler_registers_cleanup_jobs(db_session):
    db, connection = db_session
    session_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)

    await start_scheduler(session_factory)

    try:
        jobs = scheduler.get_jobs()
        job_ids = {j.id for j in jobs}
        assert "cleanup_expired_sessions" in job_ids
        assert "cleanup_stale_search_cache" in job_ids
    finally:
        stop_scheduler()
