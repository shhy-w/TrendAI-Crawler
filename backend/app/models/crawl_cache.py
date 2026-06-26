from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class CrawlCache(TimestampMixin, Base):
    __tablename__ = "crawl_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
