from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class WebBearerTokenStatus:
    ACTIVE = "active"
    FAILED = "failed"


class WebBearerToken(TimestampMixin, Base):
    __tablename__ = "web_bearer_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=WebBearerTokenStatus.ACTIVE, index=True, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
