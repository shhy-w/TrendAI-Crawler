from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class GuestTokenStatus:
    ACTIVE = "active"
    FAILED = "failed"


class GuestToken(TimestampMixin, Base):
    __tablename__ = "guest_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proxy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("proxies.id", ondelete="CASCADE"), index=True, nullable=True)
    guest_token: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=GuestTokenStatus.ACTIVE, index=True, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
