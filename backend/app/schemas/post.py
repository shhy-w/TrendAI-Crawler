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


class PostRead(BaseModel):
    id: int
    x_post_id: str
    keyword: str
    text: str
    author_name: Optional[str]
    author_handle: Optional[str]
    published_at: Optional[datetime]
    post_url: str
    reply_count: int
    repost_count: int
    like_count: int
    view_count: int
    crawled_at: datetime
    media_items: list[MediaRead] = []

    model_config = {"from_attributes": True}


class PostListResponse(BaseModel):
    items: list[PostRead]
    total: int
    page: int
    page_size: int
