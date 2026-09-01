from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crawler.types import CrawledMedia, CrawledNote
from app.models.crawl_cache import CrawlCache


def get_cached_notes(db: Session, source_type: str, target: str, limit: int, mode: str = "auto") -> list[CrawledNote] | None:
    now = datetime.now(timezone.utc)
    db.execute(delete(CrawlCache).where(CrawlCache.expires_at <= now))
    record = db.scalar(select(CrawlCache).where(CrawlCache.cache_key == _cache_key(source_type, target, limit, mode)))
    if not record:
        return None
    return [_deserialize_note(item) for item in record.payload.get("items", [])]


def set_cached_notes(
    db: Session,
    source_type: str,
    target: str,
    limit: int,
    notes: list[CrawledNote],
    mode: str = "auto",
) -> None:
    key = _cache_key(source_type, target, limit, mode)
    record = db.scalar(select(CrawlCache).where(CrawlCache.cache_key == key))
    if record is None:
        record = CrawlCache(cache_key=key, payload={})
        db.add(record)
    record.payload = {"items": [_serialize_note(note) for note in notes]}
    record.expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.crawler_cache_ttl_seconds)
    db.commit()


def _cache_key(source_type: str, target: str, limit: int, mode: str) -> str:
    digest = hashlib.sha256(target.encode("utf-8")).hexdigest()
    return f"xhs:{mode}:{source_type}:{limit}:{digest}"


def _serialize_note(note: CrawledNote) -> dict:
    return {
        "platform_note_id": note.platform_note_id,
        "note_type": note.note_type,
        "completeness": note.completeness,
        "title": note.title,
        "content": note.content,
        "note_url": note.note_url,
        "author_id": note.author_id,
        "author_name": note.author_name,
        "author_avatar": note.author_avatar,
        "published_at": note.published_at.isoformat() if note.published_at else None,
        "ip_location": note.ip_location,
        "like_count": note.like_count,
        "collect_count": note.collect_count,
        "comment_count": note.comment_count,
        "share_count": note.share_count,
        "media_items": [media.__dict__ for media in note.media_items],
        "raw_data": note.raw_data,
    }


def _deserialize_note(payload: dict) -> CrawledNote:
    published_at = datetime.fromisoformat(payload["published_at"]) if payload.get("published_at") else None
    return CrawledNote(
        platform_note_id=payload["platform_note_id"],
        note_type=payload.get("note_type", "normal"),
        completeness=payload.get("completeness", "card"),
        title=payload.get("title", ""),
        content=payload.get("content", ""),
        note_url=payload["note_url"],
        author_id=payload.get("author_id"),
        author_name=payload.get("author_name"),
        author_avatar=payload.get("author_avatar"),
        published_at=published_at,
        ip_location=payload.get("ip_location"),
        like_count=payload.get("like_count", 0),
        collect_count=payload.get("collect_count", 0),
        comment_count=payload.get("comment_count", 0),
        share_count=payload.get("share_count", 0),
        media_items=[CrawledMedia(**item) for item in payload.get("media_items", [])],
        raw_data=payload.get("raw_data"),
    )
