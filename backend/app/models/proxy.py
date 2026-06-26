from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ProxyStatus:
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    DISABLED = "disabled"


class Proxy(TimestampMixin, Base):
    __tablename__ = "proxies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    proxy_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=ProxyStatus.ACTIVE, index=True, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cooldown_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
