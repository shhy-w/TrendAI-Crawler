from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class AccountProtectionUpdate(BaseModel):
    protection_enabled: bool
    daily_request_limit: int = Field(ge=10, le=500)
    cooldown_seconds: int = Field(ge=5, le=600)
    failure_threshold: int = Field(ge=1, le=10)
    lockout_minutes: int = Field(ge=15, le=1440)


class CrawlerSessionRead(BaseModel):
    id: int
    name: str
    status: str
    last_verified_at: Optional[datetime]
    last_error: Optional[str]
    protection_enabled: bool
    daily_request_limit: int
    daily_request_count: int
    daily_request_date: Optional[date]
    cooldown_seconds: int
    failure_threshold: int
    lockout_minutes: int
    consecutive_failures: int
    last_request_at: Optional[datetime]
    blocked_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
