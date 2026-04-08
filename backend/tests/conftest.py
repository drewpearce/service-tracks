import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import create_app
from app.models.church_user import ChurchUser
from app.utils.encryption import generate_encryption_key

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://worship_flow:worship_flow@localhost:5432/service_tracks_test",
)


@pytest.fixture(scope="session", autouse=True)
def test_encryption_key():
    """Ensure ENCRYPTION_KEY is set for the entire test session.

    The app's .env lives at the repo root (not in backend/), so pydantic-settings
    does not load it when tests run from backend/. This fixture patches the settings
    object directly so encrypt()/decrypt() work throughout the test suite.
    """
    from app.config import settings

    if not settings.ENCRYPTION_KEY:
        key = generate_encryption_key()
        settings.ENCRYPTION_KEY = key


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset slowapi rate limiter state before each test to prevent cross-test 429s."""
    from app.rate_limit import limiter

    if hasattr(limiter, "_storage") and hasattr(limiter._storage, "storage"):
        limiter._storage.storage.clear()
    elif hasattr(limiter, "_storage"):
        try:
            limiter._storage = {}
        except (TypeError, AttributeError):
            pass  # storage type doesn't support direct reset; tests may need ordering care
    yield


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[tuple[AsyncSession, AsyncConnection], None]:
    connection: AsyncConnection = await test_engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)
    session = session_factory()
    yield session, connection
    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def app(db_session):
    session, connection = db_session
    application = create_app()

    async def override_get_db():
        yield session

    application.dependency_overrides[get_db] = override_get_db

    # Override the session factory on app.state so the auth middleware
    # uses the same test DB connection (not the module-level production factory).
    # Bind to the AsyncConnection directly (not the sync connection via get_bind()).
    test_session_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)
    application.state.session_factory = test_session_factory

    return application


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def db(db_session) -> AsyncSession:
    """Convenience fixture: just the AsyncSession (unwraps the (session, connection) tuple)."""
    session, _connection = db_session
    return session


@pytest_asyncio.fixture
async def registered_user(client):
    """Register a test user and return the response data + session cookie."""
    with patch("app.utils.email.send_email", new_callable=AsyncMock):
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
                "church_name": "Test Church",
            },
        )
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def authenticated_client(client, registered_user) -> AsyncClient:
    """Client with a valid session cookie (set by registration)."""
    return client


@pytest_asyncio.fixture
def mock_send_email():
    """Mock email sending to prevent real API calls in tests."""
    with patch("app.utils.email.send_email", new_callable=AsyncMock) as mock:
        yield mock


@pytest_asyncio.fixture
async def verified_authenticated_client(client, db: AsyncSession) -> AsyncClient:
    """Client with a valid session cookie for a user whose email is verified.

    PCO endpoints require require_verified_email, so tests that call them must
    use this fixture instead of authenticated_client.
    """
    with patch("app.utils.email.send_email", new_callable=AsyncMock):
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "verified@example.com",
                "password": "testpassword123",
                "church_name": "Verified Church",
            },
        )
    assert response.status_code == 201

    # Set email_verified=True directly in the DB
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == "verified@example.com"))
    user = result.scalar_one()
    user.email_verified = True
    await db.flush()

    return client
