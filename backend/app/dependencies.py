from fastapi import HTTPException, Request


async def require_auth(request: Request) -> None:
    """Require the user to be authenticated (session valid).

    Does NOT check email_verified. Used by endpoints that must be accessible
    to unverified users (e.g., the dashboard setup checklist).
    """
    user = getattr(request.state, "current_user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")


async def require_verified_email(request: Request) -> None:
    user = getattr(request.state, "current_user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="email_not_verified")
