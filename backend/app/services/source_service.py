from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.source import Source, SourceType


def create_source(db: Session, name: str, source_type: str, target: str) -> Source:
    normalized_name = name.strip()
    normalized_target = target.strip()
    if source_type not in SourceType.VALUES:
        raise ValueError("信源类型必须是 explore、keyword、profile 或 note。")
    if not normalized_name or not normalized_target:
        raise ValueError("信源名称和目标不能为空。")
    if source_type == SourceType.EXPLORE:
        if normalized_target not in {"homefeed_recommend", "fashion_v3", "food_v3", "travel_v3", "career_v3"}:
            raise ValueError("不支持的发现页频道。")
    elif source_type != SourceType.KEYWORD:
        parsed = urlparse(normalized_target)
        if parsed.scheme != "https" or parsed.netloc not in {"xiaohongshu.com", "www.xiaohongshu.com"}:
            raise ValueError("博主和笔记信源必须使用 https://www.xiaohongshu.com 链接。")
        expected = "/user/profile/" if source_type == SourceType.PROFILE else "/explore/"
        if expected not in parsed.path and not (source_type == SourceType.NOTE and "/discovery/item/" in parsed.path):
            raise ValueError("信源链接与所选类型不匹配。")
    existing = db.scalar(select(Source).where(Source.source_type == source_type, Source.target == normalized_target))
    if existing:
        raise ValueError("该信源已经存在。")
    source = Source(name=normalized_name, source_type=source_type, target=normalized_target, enabled=True)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def set_source_enabled(db: Session, source_id: int, enabled: bool) -> Source:
    source = db.get(Source, source_id)
    if not source:
        raise LookupError("Source not found")
    source.enabled = enabled
    db.commit()
    db.refresh(source)
    return source
