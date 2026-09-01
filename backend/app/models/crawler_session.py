from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class CrawlerSessionStatus:
    UNKNOWN = "unknown"
    ACTIVE = "active"
    AUTH_REQUIRED = "auth_required"
    VERIFYING = "verifying"
    LOGIN_RUNNING = "login_running"
    ERROR = "error"
    PROTECTION_BLOCKED = "protection_blocked"


class CrawlerSession(TimestampMixin, Base):
    __tablename__ = "crawler_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default=CrawlerSessionStatus.UNKNOWN, nullable=False)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    protection_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_request_limit: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    daily_request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_request_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    failure_threshold: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    lockout_minutes: Mapped[int] = mapped_column(Integer, default=360, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_request_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
