import re
import secrets as stdlib_secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.church import Church
from app.models.church_user import ChurchUser
from app.models.user_session import UserSession

SESSION_EXPIRY_DAYS = 7


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:90]  # leave room for 6-char hex suffix within 100-char column


async def generate_unique_slug(db: AsyncSession, church_name: str) -> str:
    base_slug = slugify(church_name)
    slug = base_slug
    result = await db.execute(select(Church).where(Church.slug == slug))
    if result.scalar_one_or_none() is None:
        return slug
    slug = f"{base_slug}-{stdlib_secrets.token_hex(3)}"
    return slug


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


async def create_session(db: AsyncSession, user_id: uuid.UUID, church_id: uuid.UUID) -> str:
    token = stdlib_secrets.token_urlsafe(32)
    session = UserSession(
        id=token,
        user_id=user_id,
        church_id=church_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS),
    )
    db.add(session)
    await db.flush()
    return token


async def get_valid_session(db: AsyncSession, token: str) -> UserSession | None:
    result = await db.execute(
        select(UserSession).where(
            UserSession.id == token,
            UserSession.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def delete_session(db: AsyncSession, token: str) -> None:
    await db.execute(delete(UserSession).where(UserSession.id == token))


async def delete_all_user_sessions(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(delete(UserSession).where(UserSession.user_id == user_id))


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


async def register_user(
    db: AsyncSession, email: str, password: str, church_name: str
) -> tuple[ChurchUser, Church]:
    # Check duplicate email
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == email))
    if result.scalar_one_or_none() is not None:
        raise ValueError("email_already_exists")

    slug = await generate_unique_slug(db, church_name)
    church = Church(name=church_name, slug=slug)
    db.add(church)
    await db.flush()

    user = ChurchUser(
        church_id=church.id,
        email=email,
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.flush()
    return user, church


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def authenticate_user(db: AsyncSession, email: str, password: str) -> ChurchUser | None:
    result = await db.execute(select(ChurchUser).where(ChurchUser.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
