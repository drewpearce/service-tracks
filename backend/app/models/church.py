import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Church(Base):
    __tablename__ = "church"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    pco_service_type_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    playlist_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="shared")
    playlist_name_template: Mapped[str] = mapped_column(Text, nullable=False, default="{church_name} Worship")
    playlist_description_template: Mapped[str] = mapped_column(Text, nullable=False, default="Worship set for {date}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    users: Mapped[list["ChurchUser"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ChurchUser", back_populates="church", lazy="selectin"
    )
    pco_connection: Mapped["PcoConnection | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "PcoConnection", back_populates="church", uselist=False, lazy="selectin"
    )
    streaming_connections: Mapped[list["StreamingConnection"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "StreamingConnection", back_populates="church", lazy="selectin"
    )
    song_mappings: Mapped[list["SongMapping"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "SongMapping", back_populates="church", lazy="selectin"
    )
    playlists: Mapped[list["Playlist"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Playlist", back_populates="church", lazy="selectin"
    )
    sync_logs: Mapped[list["SyncLog"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "SyncLog", back_populates="church", lazy="selectin"
    )
    user_sessions: Mapped[list["UserSession"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "UserSession", back_populates="church", lazy="selectin"
    )
