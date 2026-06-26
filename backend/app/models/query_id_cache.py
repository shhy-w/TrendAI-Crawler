from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class QueryIdCache(TimestampMixin, Base):
    __tablename__ = "query_id_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    query_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
