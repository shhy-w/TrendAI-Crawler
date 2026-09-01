from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MediaRead(BaseModel):
    id: int
    media_type: str
    media_url: str
    thumbnail_url: Optional[str]
    width: Optional[int]
    height: Optional[int]
    sort_order: int

    model_config = {"from_attributes": True}


class NoteSourceRead(BaseModel):
    source_id: int
    discovered_at: datetime
    last_seen_at: datetime

    model_config = {"from_attributes": True}


class NoteRead(BaseModel):
    id: int
    platform_note_id: str
    note_type: str
    completeness: str
    title: str
    content: str
    author_id: Optional[str]
    author_name: Optional[str]
    author_avatar: Optional[str]
    published_at: Optional[datetime]
    ip_location: Optional[str]
    note_url: str
    like_count: int
    collect_count: int
    comment_count: int
    share_count: int
    crawled_at: datetime
    media_items: list[MediaRead] = []
    source_links: list[NoteSourceRead] = []

    model_config = {"from_attributes": True}


class NoteListResponse(BaseModel):
    items: list[NoteRead]
    total: int
    page: int
    page_size: int


class NoteStatsRead(BaseModel):
    total_notes: int
    added_last_24h: int
    active_sources: int
    total_sources: int
