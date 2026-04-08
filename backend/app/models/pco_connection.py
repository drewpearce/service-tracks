import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PcoConnection(Base):
    __tablename__ = "pco_connection"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("church.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    auth_method: Mapped[str] = mapped_column(String(20), default="api_key", nullable=False)
    app_id_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    secret_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    oauth_access_token_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    oauth_refresh_token_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_call_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    church: Mapped["Church"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Church", back_populates="pco_connection", lazy="selectin"
    )
