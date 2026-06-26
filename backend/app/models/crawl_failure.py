from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import utcnow


class CrawlFailure(Base):
    __tablename__ = "crawl_failures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("crawl_jobs.id", ondelete="SET NULL"), nullable=True)
    keyword: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    failure_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    debug_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    proxy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("proxies.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
