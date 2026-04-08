import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SongMapping(Base):
    __tablename__ = "song_mapping"
    __table_args__ = (
        UniqueConstraint("church_id", "pco_song_id", "platform", name="uq_song_mapping_church_song_platform"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("church.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pco_song_id: Mapped[str] = mapped_column(String(50), nullable=False)
    pco_song_title: Mapped[str] = mapped_column(String(500), nullable=False)
    pco_song_artist: Mapped[str | None] = mapped_column(String(500), nullable=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    track_id: Mapped[str] = mapped_column(String(255), nullable=False)
    track_title: Mapped[str] = mapped_column(String(500), nullable=False)
    track_artist: Mapped[str | None] = mapped_column(String(500), nullable=True)
    matched_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("church_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    church: Mapped["Church"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Church", back_populates="song_mappings", lazy="selectin"
    )
    matched_by_user: Mapped["ChurchUser | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ChurchUser", back_populates="song_mappings", lazy="selectin"
    )
