from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CrawlerSessionRead(BaseModel):
    id: int
    name: str
    status: str
    last_verified_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
