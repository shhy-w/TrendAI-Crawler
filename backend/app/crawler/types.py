from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CrawledMedia:
    media_type: str
    media_url: str
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    sort_order: int = 0


@dataclass
class CrawledPost:
    x_post_id: str
    keyword: str
    text: str
    author_name: str | None
    author_handle: str | None
    published_at: datetime | None
    post_url: str
    reply_count: int = 0
    repost_count: int = 0
    like_count: int = 0
    view_count: int = 0
    media_items: list[CrawledMedia] = field(default_factory=list)
