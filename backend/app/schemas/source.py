from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source_type: str
    target: str = Field(min_length=1, max_length=2048)


class SourceUpdate(BaseModel):
    enabled: bool


class SourceRead(BaseModel):
    id: int
    name: str
    source_type: str
    target: str
    enabled: bool
    last_run_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_result_count: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
