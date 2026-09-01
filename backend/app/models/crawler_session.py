from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
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


class CrawlerSession(TimestampMixin, Base):
    __tablename__ = "crawler_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default=CrawlerSessionStatus.UNKNOWN, nullable=False)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
