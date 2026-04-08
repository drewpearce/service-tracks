import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("church.id", ondelete="CASCADE"), nullable=False, index=True
    )
    playlist_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("playlist.id", ondelete="SET NULL"), nullable=True
    )
    sync_trigger: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    songs_total: Mapped[int] = mapped_column(Integer, nullable=False)
    songs_matched: Mapped[int] = mapped_column(Integer, nullable=False)
    songs_unmatched: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    church: Mapped["Church"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Church", back_populates="sync_logs", lazy="selectin"
    )
    playlist: Mapped["Playlist | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Playlist", back_populates="sync_logs", lazy="selectin"
    )
