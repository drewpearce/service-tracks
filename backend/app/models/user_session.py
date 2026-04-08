import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserSession(Base):
    __tablename__ = "user_session"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("church_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    church_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("church.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    user: Mapped["ChurchUser"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ChurchUser", back_populates="user_sessions", lazy="selectin"
    )
    church: Mapped["Church"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Church", back_populates="user_sessions", lazy="selectin"
    )
