from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CrawledMedia:
    media_type: str
    media_url: str
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    sort_order: int = 0
    quality: str = "preview"


@dataclass
class CrawledNote:
    platform_note_id: str
    note_type: str
    completeness: str
    title: str
    content: str
    note_url: str
    author_id: str | None
    author_name: str | None
    author_avatar: str | None
    published_at: datetime | None
    ip_location: str | None = None
    like_count: int = 0
    collect_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    media_items: list[CrawledMedia] = field(default_factory=list)
    raw_data: dict[str, Any] | None = None
