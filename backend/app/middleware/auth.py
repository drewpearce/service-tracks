import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.services.auth_service import get_valid_session

EXEMPT_PATTERNS = [
    re.compile(r"^/api/health$"),
    re.compile(r"^/api/auth/login$"),
    re.compile(r"^/api/auth/register$"),
    re.compile(r"^/api/auth/forgot-password$"),
    re.compile(r"^/api/auth/reset-password$"),
    re.compile(r"^/api/auth/verify-email$"),
    re.compile(r"^/api/webhooks"),
    re.compile(r"^/api/streaming/spotify/callback$"),
]


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Serve frontend assets without auth
        if not path.startswith("/api/"):
            return await call_next(request)

        # Exempt auth-related endpoints
        for pattern in EXEMPT_PATTERNS:
            if pattern.match(path):
                return await call_next(request)

        # Require session cookie
        token = request.cookies.get("session")
        if not token:
            return JSONResponse(status_code=401, content={"error": "not_authenticated"})

        # Validate session using the app-state session factory (not a direct import)
        # so that test overrides work correctly.
        session_factory = request.app.state.session_factory
        async with session_factory() as db_session:
            session_row = await get_valid_session(db_session, token)
            if session_row is None:
                return JSONResponse(status_code=401, content={"error": "not_authenticated"})

            # UserSession.user is loaded via lazy="selectin"
            request.state.current_user = session_row.user
            request.state.church_id = session_row.church_id

        response = await call_next(request)
        return response
