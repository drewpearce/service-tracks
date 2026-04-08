import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Playlist(Base):
    __tablename__ = "playlist"
    __table_args__ = (
        UniqueConstraint("church_id", "pco_plan_id", "platform", name="uq_playlist_church_plan_platform"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("church.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pco_plan_id: Mapped[str] = mapped_column(String(50), nullable=False)
    pco_plan_date: Mapped[date] = mapped_column(Date, nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    external_playlist_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_playlist_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    last_known_track_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    church: Mapped["Church"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Church", back_populates="playlists", lazy="selectin"
    )
    sync_logs: Mapped[list["SyncLog"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "SyncLog", back_populates="playlist", lazy="selectin"
    )
