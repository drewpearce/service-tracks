import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

DEFAULT_PLAYLIST_MODE = "shared"
DEFAULT_NAME_TEMPLATE = "{church_name} Worship"
DEFAULT_DESCRIPTION_TEMPLATE = "Worship set for {date}"


class StreamingSettings(Base):
    __tablename__ = "streaming_settings"
    __table_args__ = (UniqueConstraint("church_id", "platform", name="uq_streaming_settings_church_platform"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("church.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    playlist_mode: Mapped[str] = mapped_column(String(20), nullable=False, default=DEFAULT_PLAYLIST_MODE)
    playlist_name_template: Mapped[str] = mapped_column(Text, nullable=False, default=DEFAULT_NAME_TEMPLATE)
    playlist_description_template: Mapped[str] = mapped_column(
        Text, nullable=False, default=DEFAULT_DESCRIPTION_TEMPLATE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    church: Mapped["Church"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Church", back_populates="streaming_settings", lazy="selectin"
    )
