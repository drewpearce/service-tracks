import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class YouTubeQuotaUsage(Base):
    __tablename__ = "youtube_quota_usage"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    units_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
