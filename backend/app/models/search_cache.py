import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SearchCache(Base):
    __tablename__ = "search_cache"
    __table_args__ = (UniqueConstraint("platform", "query", name="uq_search_cache_platform_query"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    results: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
