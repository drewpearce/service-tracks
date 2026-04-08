import re
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette_csrf import CSRFMiddleware

from app.config import settings
from app.database import async_session_factory
from app.middleware.auth import AuthMiddleware
from app.rate_limit import limiter
from app.routers import auth, dashboard, health, pco, plans, songs, streaming, webhooks
from app.routers import settings as settings_router
from app.scheduler import start_scheduler, stop_scheduler
from app.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    setup_logging()
    await start_scheduler(async_session_factory)
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    """FastAPI application factory."""
    # Initialize Sentry
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.1,
        )

    app = FastAPI(
        title="ServiceTracks",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Store session factory on app.state so auth middleware can access it without
    # a direct module import (critical for test DB override — see middleware/auth.py).
    app.state.session_factory = async_session_factory

    # Middleware — Starlette uses LIFO ordering: last add_middleware call becomes outermost.
    # Desired execution order: CSRF (outermost) → CORS → Auth (innermost) → handler.
    # So registration order must be: Auth first, then CORS, then CSRF last.

    # AuthMiddleware (innermost — registered FIRST)
    app.add_middleware(AuthMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # CSRF middleware (outermost — registered LAST)
    # Explicitly set cookie_name and header_name to match the frontend client.
    # starlette-csrf v3 defaults to "csrftoken" / "x-csrftoken", but we use
    # "csrf_token" / "x-csrf-token" to match the architecture doc convention.
    # exempt_urls expects List[re.Pattern], not plain strings.
    app.add_middleware(
        CSRFMiddleware,
        secret=settings.CSRF_SECRET,
        cookie_name="csrf_token",
        header_name="x-csrf-token",
        exempt_urls=[
            re.compile(r"^/api/health$"),
            re.compile(r"^/api/auth/login$"),
            re.compile(r"^/api/auth/register$"),
            re.compile(r"^/api/auth/forgot-password$"),
            re.compile(r"^/api/auth/reset-password$"),
            re.compile(r"^/api/auth/verify-email$"),
            re.compile(r"^/api/webhooks"),
        ],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(pco.router)
    app.include_router(streaming.router)
    app.include_router(songs.router)
    app.include_router(plans.router)
    app.include_router(dashboard.router)
    app.include_router(webhooks.router)
    app.include_router(settings_router.router)

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            schema_paths = {"docs", "redoc", "openapi.json"}
            if full_path.startswith(("api/", "docs/", "redoc/")) or full_path in schema_paths:
                raise HTTPException(status_code=404)
            return FileResponse(static_dir / "index.html")

    return app


app = create_app()
