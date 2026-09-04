from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.core.config import settings
from app.crawler.errors import CrawlFailureType, classify_exception
from app.crawler.xhs_crawler import XHSCrawler
from app.models.media import Media
from app.models.note import Note
from app.models.note_source import NoteSource
from app.models.source import Source
from app.schemas.note import NoteListResponse, NoteRead, NoteStatsRead
from app.services.account_protection_service import (
    record_authenticated_failure,
    record_authenticated_success,
    reserve_authenticated_access,
)
from app.services.crawl_service import upsert_notes
from app.services.media_archive_service import archive_note_media


router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=NoteListResponse)
def list_notes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    query: Optional[str] = None,
    author: Optional[str] = None,
    source_id: Optional[int] = None,
    note_type: Optional[str] = None,
    has_media: Optional[bool] = None,
    sort: str = Query(default="engagement", pattern="^(engagement|published_at|crawled_at)$"),
    db: Session = Depends(get_db),
) -> NoteListResponse:
    statement = select(Note).options(selectinload(Note.media_items), selectinload(Note.source_links))
    statement = _apply_filters(statement, query, author, source_id, note_type, has_media)
    count_statement = _apply_filters(select(func.count()).select_from(Note), query, author, source_id, note_type, has_media)
    total = db.scalar(count_statement) or 0
    if sort == "engagement":
        statement = statement.order_by((Note.like_count + Note.collect_count * 2 + Note.comment_count + Note.share_count).desc())
    elif sort == "published_at":
        statement = statement.order_by(Note.published_at.desc())
    else:
        statement = statement.order_by(Note.crawled_at.desc())
    items = list(db.scalars(statement.offset((page - 1) * page_size).limit(page_size)))
    return NoteListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/stats", response_model=NoteStatsRead)
def get_note_stats(db: Session = Depends(get_db)) -> NoteStatsRead:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    return NoteStatsRead(
        total_notes=db.scalar(select(func.count()).select_from(Note)) or 0,
        added_last_24h=db.scalar(select(func.count()).select_from(Note).where(Note.created_at >= cutoff)) or 0,
        active_sources=db.scalar(select(func.count()).select_from(Source).where(Source.enabled.is_(True))) or 0,
        total_sources=db.scalar(select(func.count()).select_from(Source)) or 0,
    )


@router.get("/{note_id}", response_model=NoteRead)
def get_note(note_id: int, db: Session = Depends(get_db)) -> Note:
    note = db.get(Note, note_id, options=[selectinload(Note.media_items), selectinload(Note.source_links)])
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/{note_id}/archive-media", response_model=NoteRead)
async def archive_media(note_id: int, db: Session = Depends(get_db)) -> Note:
    note = db.get(Note, note_id, options=[selectinload(Note.media_items), selectinload(Note.source_links)])
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    await archive_note_media(db, note)
    return db.get(Note, note_id, options=[selectinload(Note.media_items), selectinload(Note.source_links)])


@router.post("/{note_id}/enrich", response_model=NoteRead)
async def enrich_note(note_id: int, db: Session = Depends(get_db)) -> Note:
    note = db.get(Note, note_id, options=[selectinload(Note.media_items), selectinload(Note.source_links)])
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    try:
        wait_seconds = reserve_authenticated_access(db, cost=1 + settings.crawler_scroll_rounds)
        if wait_seconds:
            await asyncio.sleep(wait_seconds)
        crawled_notes = await XHSCrawler().crawl_source("note", note.note_url, 1, "authenticated")
        matching = next((item for item in crawled_notes if item.platform_note_id == note.platform_note_id), None)
        if not matching:
            raise RuntimeError("详情响应中未找到目标笔记。")
        upsert_notes(db, [matching], source=None)
        record_authenticated_success(db)
        enriched = db.scalar(
            select(Note)
            .where(Note.id == note_id)
            .options(selectinload(Note.media_items), selectinload(Note.source_links))
        )
        await archive_note_media(db, enriched)
        return enriched
    except Exception as exc:
        classified = classify_exception(exc)
        record_authenticated_failure(db, classified.failure_type, classified.message)
        status_code = 409 if classified.failure_type in {
            CrawlFailureType.AUTH_REQUIRED,
            CrawlFailureType.PROTECTION_BLOCKED,
        } else 502
        raise HTTPException(status_code=status_code, detail=classified.message) from exc


def _apply_filters(
    statement: Select,
    query: Optional[str],
    author: Optional[str],
    source_id: Optional[int],
    note_type: Optional[str],
    has_media: Optional[bool],
) -> Select:
    if query:
        pattern = f"%{query}%"
        statement = statement.where(or_(Note.title.like(pattern), Note.content.like(pattern)))
    if author:
        statement = statement.where(Note.author_name.like(f"%{author}%"))
    if source_id:
        statement = statement.where(Note.id.in_(select(NoteSource.note_id).where(NoteSource.source_id == source_id)))
    if note_type:
        statement = statement.where(Note.note_type == note_type)
    if has_media is True:
        statement = statement.where(Note.id.in_(select(Media.note_id)))
    elif has_media is False:
        statement = statement.where(Note.id.not_in(select(Media.note_id)))
    return statement
