from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, utcnow


class NoteCompleteness:
    CARD = "card"
    PARTIAL = "partial"
    COMPLETE = "complete"
    RANK = {CARD: 0, PARTIAL: 1, COMPLETE: 2}


class Note(TimestampMixin, Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_note_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    note_type: Mapped[str] = mapped_column(String(32), default="normal", index=True, nullable=False)
    completeness: Mapped[str] = mapped_column(String(32), default=NoteCompleteness.CARD, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    author_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    author_name: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    author_avatar: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    ip_location: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    note_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    collect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    share_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True, nullable=False)
    raw_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    media_items: Mapped[List["Media"]] = relationship(
        back_populates="note",
        cascade="all, delete-orphan",
        order_by="Media.sort_order",
        lazy="selectin",
    )
    source_links: Mapped[List["NoteSource"]] = relationship(
        back_populates="note",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    metric_snapshots: Mapped[List["NoteMetricSnapshot"]] = relationship(
        back_populates="note",
        cascade="all, delete-orphan",
    )
