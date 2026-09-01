from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CrawlJobCreate(BaseModel):
    source_ids: list[int] = Field(min_length=1)
    max_notes_per_source: int = Field(default=20, ge=1, le=100)


class CrawlJobItemRead(BaseModel):
    id: int
    source_id: Optional[int]
    source_name: str
    source_type: str
    target: str
    status: str
    discovered_count: int
    saved_count: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CrawlJobRead(BaseModel):
    id: int
    status: str
    max_notes_per_source: int
    total_sources: int
    completed_sources: int
    discovered_count: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    success_count: int
    failure_type: Optional[str]
    debug_path: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    items: list[CrawlJobItemRead] = []

    model_config = {"from_attributes": True}
