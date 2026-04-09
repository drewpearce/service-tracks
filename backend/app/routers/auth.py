import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.church_user import ChurchUser
from app.rate_limit import limiter
from app.schemas.auth import (
    ChurchResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    UserResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.services import auth_service
from app.services.auth_service import delete_all_user_sessions
from app.utils.email import send_password_reset_email, send_verification_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

VERIFICATION_TOKEN_EXPIRY = timedelta(hours=24)
RESEND_COOLDOWN = timedelta(minutes=2)
RESET_TOKEN_EXPIRY = timedelta(hours=1)


def _build_user_response(user: ChurchUser) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        email_verified=user.email_verified,
        church_id=str(user.church_id),
        role=user.role,
    )


def _build_church_response(church) -> ChurchResponse:
    return ChurchResponse(
        id=str(church.id),
        name=church.name,
        slug=church.slug,
    )


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------


@router.post("/register", status_code=201)
@limiter.limit("10/minute")
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user, church = await auth_service.register_user(db, body.email, body.password, body.church_name)
    except ValueError as exc:
        if str(exc) == "email_already_exists":
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        raise

    # Generate email verification token
    verification_token = secrets.token_urlsafe(32)
    user.email_verification_token = verification_token
    user.email_verification_sent_at = datetime.now(timezone.utc)

    # Create session
    session_token = await auth_service.create_session(db, user.id, church.id)

    # Send verification email — on failure roll back by re-raising an HTTPException
    # (get_db rolls back the transaction on any exception, so no orphaned records)
    try:
        await send_verification_email(user.email, verification_token)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Your account could not be created because the verification email failed to send. Please try again.",
        )

    response_data = RegisterResponse(
        user=_build_user_response(user),
        church=_build_church_response(church),
        message="Verification email sent. Please check your inbox.",
    )

    response = JSONResponse(content=response_data.model_dump(), status_code=201)
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
        max_age=604800,  # 7 days
    )
    return response


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------


@router.post("/login")
@limiter.limit("10/minute")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate_user(db, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    session_token = await auth_service.create_session(db, user.id, user.church_id)

    response_data = LoginResponse(user=_build_user_response(user))
    response = JSONResponse(content=response_data.model_dump(), status_code=200)
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
        max_age=604800,  # 7 days
    )
    return response


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------


@router.post("/logout", status_code=204)
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("session")
    if token:
        await auth_service.delete_session(db, token)

    response = JSONResponse(content=None, status_code=204)
    response.delete_cookie(
        key="session",
        path="/",
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
    )
    return response


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------


@router.get("/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    user = request.state.current_user
    church = user.church
    return MeResponse(
        user=_build_user_response(user),
        church=_build_church_response(church),
    )


# ---------------------------------------------------------------------------
# POST /verify-email
# ---------------------------------------------------------------------------


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ChurchUser).where(ChurchUser.email_verification_token == body.token))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="invalid_or_expired_token")
    if (
        user.email_verification_sent_at is None
        or datetime.now(timezone.utc) - user.email_verification_sent_at.replace(tzinfo=timezone.utc)
        > VERIFICATION_TOKEN_EXPIRY
    ):
        raise HTTPException(status_code=400, detail="invalid_or_expired_token")
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_sent_at = None
    return VerifyEmailResponse(email_verified=True)


# ---------------------------------------------------------------------------
# POST /resend-verification
# ---------------------------------------------------------------------------


@router.post("/resend-verification")
async def resend_verification(request: Request, db: AsyncSession = Depends(get_db)):
    user_from_middleware = request.state.current_user
    # Re-fetch user in this request's DB session to make it managed/attached
    result = await db.execute(select(ChurchUser).where(ChurchUser.id == user_from_middleware.id))
    user = result.scalar_one()

    if user.email_verified:
        return MessageResponse(message="Email already verified.")
    if (
        user.email_verification_sent_at is not None
        and datetime.now(timezone.utc) - user.email_verification_sent_at.replace(tzinfo=timezone.utc) < RESEND_COOLDOWN
    ):
        raise HTTPException(
            status_code=429,
            detail="Please wait before requesting another verification email.",
        )

    token = secrets.token_urlsafe(32)
    user.email_verification_token = token
    user.email_verification_sent_at = datetime.now(timezone.utc)
    await send_verification_email(user.email, token)
    return MessageResponse(message="Verification email sent.")


# ---------------------------------------------------------------------------
# POST /forgot-password
# ---------------------------------------------------------------------------


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == body.email))
    user = result.scalar_one_or_none()
    if user is not None:
        raw_token = secrets.token_urlsafe(32)
        hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()
        user.password_reset_token = hashed_token
        user.password_reset_sent_at = datetime.now(timezone.utc)
        await send_password_reset_email(user.email, raw_token)
    # Always return 200 — no email enumeration
    return MessageResponse(message="If an account with that email exists, a reset link has been sent.")


# ---------------------------------------------------------------------------
# POST /reset-password
# ---------------------------------------------------------------------------


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    hashed = hashlib.sha256(body.token.encode()).hexdigest()
    result = await db.execute(select(ChurchUser).where(ChurchUser.password_reset_token == hashed))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="invalid_or_expired_token")
    if (
        user.password_reset_sent_at is None
        or datetime.now(timezone.utc) - user.password_reset_sent_at.replace(tzinfo=timezone.utc) > RESET_TOKEN_EXPIRY
    ):
        raise HTTPException(status_code=400, detail="invalid_or_expired_token")

    user.password_hash = auth_service.hash_password(body.new_password)
    user.password_reset_token = None
    user.password_reset_sent_at = None
    await delete_all_user_sessions(db, user.id)
    await db.flush()
    return MessageResponse(message="Password has been reset. Please log in.")
