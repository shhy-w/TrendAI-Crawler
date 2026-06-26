from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class CrawlJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CrawlJob(TimestampMixin, Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default=CrawlJobStatus.PENDING.value, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    max_posts_per_keyword: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_type: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    debug_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
