from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.config import settings


class CrawlJobCreate(BaseModel):
    keywords: list[str] = Field(default_factory=lambda: settings.default_keyword_list, min_length=1)
    max_posts_per_keyword: int = Field(default=20, ge=1, le=100)


class CrawlJobRead(BaseModel):
    id: int
    status: str
    keywords: list[str]
    max_posts_per_keyword: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    success_count: int
    failure_type: Optional[str]
    debug_path: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
