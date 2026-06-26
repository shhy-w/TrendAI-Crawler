from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProxyRead(BaseModel):
    id: int
    name: str
    proxy_url: str
    status: str
    failure_count: int
    success_count: int
    last_error: Optional[str]
    last_checked_at: Optional[datetime]
    cooldown_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProxyCreate(BaseModel):
    name: str
    proxy_url: str


class ProxyCheckResult(BaseModel):
    proxy_id: int
    status: str
    message: str
    guest_token_ok: bool


class GuestTokenRead(BaseModel):
    id: int
    proxy_id: Optional[int]
    status: str
    failure_count: int
    last_error: Optional[str]
    expires_at: datetime
    last_success_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QueryIdCacheRead(BaseModel):
    id: int
    operation_name: str
    query_id: str
    source_url: Optional[str]
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CrawlFailureRead(BaseModel):
    id: int
    job_id: Optional[int]
    keyword: Optional[str]
    failure_type: str
    message: str
    debug_path: Optional[str]
    proxy_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
