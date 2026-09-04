from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.crawler.errors import CrawlFailureType, classify_exception
from app.crawler.types import CrawledMedia, CrawledNote
from app.crawler.xhs_crawler import XHSCrawler
from app.db.session import SessionLocal
from app.models.crawl_job import CrawlJob, CrawlJobStatus, CrawlMode
from app.models.crawl_job_item import CrawlJobItem
from app.models.crawler_session import CrawlerSessionStatus
from app.models.media import Media
from app.models.note import Note, NoteCompleteness
from app.models.note_metric_snapshot import NoteMetricSnapshot
from app.models.note_source import NoteSource
from app.models.source import Source, SourceType
from app.services.account_protection_service import (
    record_authenticated_failure,
    record_authenticated_success,
    reserve_authenticated_access,
)
from app.services.cache_service import get_cached_notes, set_cached_notes
from app.services.media_archive_service import archive_note_media
from app.services.session_service import get_or_create_session


def create_crawl_job(
    db: Session,
    source_ids: list[int],
    max_notes_per_source: int,
    crawl_mode: str = CrawlMode.AUTO,
) -> CrawlJob:
    if crawl_mode not in CrawlMode.VALUES:
        raise ValueError("采集模式必须是 auto、public 或 authenticated。")
    normalized_ids = list(dict.fromkeys(source_ids))
    sources = list(db.scalars(select(Source).where(Source.id.in_(normalized_ids), Source.enabled.is_(True))))
    source_by_id = {source.id: source for source in sources}
    ordered_sources = [source_by_id[source_id] for source_id in normalized_ids if source_id in source_by_id]
    if not ordered_sources:
        raise ValueError("至少选择一个已启用的信源。")
    job = CrawlJob(
        status=CrawlJobStatus.PENDING.value,
        crawl_mode=crawl_mode,
        max_notes_per_source=max_notes_per_source,
        total_sources=len(ordered_sources),
        completed_sources=0,
        discovered_count=0,
        success_count=0,
    )
    for source in ordered_sources:
        job.items.append(
            CrawlJobItem(
                source_id=source.id,
                source_name=source.name,
                source_type=source.source_type,
                target=source.target,
                status=CrawlJobStatus.PENDING.value,
            )
        )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_crawl_job(job_id: int) -> None:
    asyncio.run(_run_crawl_job(job_id))


async def _run_crawl_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(CrawlJob, job_id, options=[selectinload(CrawlJob.items)])
        if not job:
            return
        job.status = CrawlJobStatus.RUNNING.value
        job.started_at = datetime.now(timezone.utc)
        job.failure_type = None
        job.debug_path = None
        job.error_message = None
        db.commit()
        crawler = XHSCrawler()
        failed_items = 0
        first_failure_type: str | None = None
        for item in job.items:
            used_authenticated = False
            item.status = CrawlJobStatus.RUNNING.value
            item.started_at = datetime.now(timezone.utc)
            db.commit()
            source = db.get(Source, item.source_id) if item.source_id else None
            try:
                notes = get_cached_notes(
                    db,
                    item.source_type,
                    item.target,
                    job.max_notes_per_source,
                    job.crawl_mode,
                )
                if notes is None:
                    effective_mode = job.crawl_mode
                    if effective_mode == CrawlMode.AUTO:
                        effective_mode = (
                            CrawlMode.PUBLIC
                            if item.source_type == SourceType.EXPLORE
                            else CrawlMode.AUTHENTICATED
                        )
                    used_authenticated = effective_mode == CrawlMode.AUTHENTICATED
                    if used_authenticated:
                        wait_seconds = reserve_authenticated_access(
                            db,
                            cost=1 + settings.crawler_scroll_rounds,
                        )
                        if wait_seconds:
                            await asyncio.sleep(wait_seconds)
                    notes = await crawler.crawl_source(
                        item.source_type,
                        item.target,
                        job.max_notes_per_source,
                        effective_mode,
                    )
                    if used_authenticated:
                        record_authenticated_success(db)
                    set_cached_notes(
                        db,
                        item.source_type,
                        item.target,
                        job.max_notes_per_source,
                        notes,
                        job.crawl_mode,
                    )
                item.discovered_count = len(notes)
                item.saved_count = upsert_notes(db, notes, source)
                await archive_crawled_notes(db, notes)
                item.status = CrawlJobStatus.SUCCEEDED.value
                if source:
                    source.last_run_at = datetime.now(timezone.utc)
                    source.last_success_at = source.last_run_at
                    source.last_result_count = len(notes)
                    source.last_error = None
            except Exception as exc:
                db.rollback()
                item = db.get(CrawlJobItem, item.id)
                source = db.get(Source, item.source_id) if item and item.source_id else None
                classified = classify_exception(exc)
                if used_authenticated:
                    record_authenticated_failure(db, classified.failure_type, classified.message)
                failed_items += 1
                first_failure_type = first_failure_type or classified.failure_type
                if item:
                    if classified.failure_type == CrawlFailureType.AUTH_REQUIRED:
                        item.status = "needs_auth"
                    elif classified.failure_type == CrawlFailureType.PROTECTION_BLOCKED:
                        item.status = "protection_blocked"
                    else:
                        item.status = CrawlJobStatus.FAILED.value
                    item.error_message = classified.message[:1024]
                if source:
                    source.last_run_at = datetime.now(timezone.utc)
                    source.last_error = classified.message[:1024]
                if classified.failure_type == CrawlFailureType.AUTH_REQUIRED:
                    session = get_or_create_session(db)
                    session.status = CrawlerSessionStatus.AUTH_REQUIRED
                    session.last_error = classified.message[:1024]
            finally:
                item = db.get(CrawlJobItem, item.id)
                if item:
                    item.finished_at = datetime.now(timezone.utc)
                job = db.get(CrawlJob, job_id)
                if job:
                    job.completed_sources += 1
                    job.discovered_count += item.discovered_count if item else 0
                    job.success_count += item.saved_count if item else 0
                db.commit()

        job = db.get(CrawlJob, job_id)
        if not job:
            return
        if failed_items == job.total_sources:
            job.status = CrawlJobStatus.FAILED.value
            job.error_message = "所有信源采集失败，请查看任务明细。"
        elif failed_items:
            job.status = CrawlJobStatus.PARTIAL.value
            job.error_message = f"{failed_items} 个信源采集失败。"
        else:
            job.status = CrawlJobStatus.SUCCEEDED.value
        job.failure_type = first_failure_type
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def upsert_notes(db: Session, crawled_notes: list[CrawledNote], source: Source | None) -> int:
    saved = 0
    now = datetime.now(timezone.utc)
    for crawled in crawled_notes:
        note = db.scalar(
            select(Note).where(Note.platform_note_id == crawled.platform_note_id).options(selectinload(Note.media_items))
        )
        if note is None:
            note = Note(platform_note_id=crawled.platform_note_id, title="", content="", note_url=crawled.note_url)
            db.add(note)
        note.note_type = crawled.note_type
        if NoteCompleteness.RANK.get(crawled.completeness, 0) >= NoteCompleteness.RANK.get(note.completeness, 0):
            note.completeness = crawled.completeness
        note.title = crawled.title or note.title
        note.content = crawled.content or note.content
        note.author_id = crawled.author_id or note.author_id
        note.author_name = crawled.author_name or note.author_name
        note.author_avatar = crawled.author_avatar or note.author_avatar
        note.published_at = crawled.published_at or note.published_at
        note.ip_location = crawled.ip_location or note.ip_location
        note.note_url = crawled.note_url or note.note_url
        note.like_count = crawled.like_count
        note.collect_count = crawled.collect_count
        note.comment_count = crawled.comment_count
        note.share_count = crawled.share_count
        note.crawled_at = now
        note.raw_data = crawled.raw_data or note.raw_data
        db.flush()
        if crawled.media_items:
            _merge_media_items(note, crawled.media_items)
        if source:
            link = db.scalar(select(NoteSource).where(NoteSource.note_id == note.id, NoteSource.source_id == source.id))
            if link is None:
                db.add(NoteSource(note_id=note.id, source_id=source.id, discovered_at=now, last_seen_at=now))
            else:
                link.last_seen_at = now
        db.add(
            NoteMetricSnapshot(
                note_id=note.id,
                like_count=note.like_count,
                collect_count=note.collect_count,
                comment_count=note.comment_count,
                share_count=note.share_count,
                captured_at=now,
            )
        )
        saved += 1
    db.commit()
    return saved


MEDIA_QUALITY_RANK = {
    "preview": 0,
    "detail": 1,
    "original": 2,
    "playback": 2,
}


def _merge_media_items(note: Note, incoming_items: list[CrawledMedia]) -> None:
    existing_by_slot = {
        (media.media_type, media.sort_order): media
        for media in note.media_items
    }
    for incoming in incoming_items:
        existing = existing_by_slot.get((incoming.media_type, incoming.sort_order))
        if existing is None:
            added = Media(**incoming.__dict__)
            note.media_items.append(added)
            existing_by_slot[(incoming.media_type, incoming.sort_order)] = added
            continue
        if incoming.media_url == existing.media_url:
            existing.thumbnail_url = incoming.thumbnail_url or existing.thumbnail_url
            if not (existing.archive_status == "archived" and existing.local_path):
                if _pixel_area(incoming.width, incoming.height) > _pixel_area(existing.width, existing.height):
                    existing.width = incoming.width
                    existing.height = incoming.height
            if _quality_rank(incoming.quality) > _quality_rank(existing.quality):
                existing.quality = incoming.quality
            continue
        if not _incoming_media_is_better(existing, incoming):
            continue
        existing.media_url = incoming.media_url
        existing.thumbnail_url = incoming.thumbnail_url
        existing.width = incoming.width
        existing.height = incoming.height
        existing.quality = incoming.quality
        _clear_archive_metadata(existing)


def _incoming_media_is_better(existing: Media, incoming: CrawledMedia) -> bool:
    existing_quality = _quality_rank(existing.quality)
    incoming_quality = _quality_rank(incoming.quality)
    if incoming_quality != existing_quality:
        return incoming_quality > existing_quality

    existing_area = _pixel_area(existing.width, existing.height)
    incoming_area = _pixel_area(incoming.width, incoming.height)
    if existing_area and incoming_area and incoming_area != existing_area:
        return incoming_area > existing_area

    # A completed archive is preferable when the new candidate has no measurable advantage.
    return not (existing.archive_status == "archived" and existing.local_path)


def _quality_rank(quality: str) -> int:
    return MEDIA_QUALITY_RANK.get(quality, 0)


def _pixel_area(width: int | None, height: int | None) -> int:
    return (width or 0) * (height or 0)


def _clear_archive_metadata(media: Media) -> None:
    media.archive_status = "remote"
    media.local_path = None
    media.mime_type = None
    media.file_size = None
    media.checksum_sha256 = None
    media.duration_seconds = None
    media.archive_error = None
    media.archived_at = None


async def archive_crawled_notes(db: Session, crawled_notes: list[CrawledNote]) -> None:
    for crawled in crawled_notes:
        note = db.scalar(
            select(Note)
            .where(Note.platform_note_id == crawled.platform_note_id)
            .options(selectinload(Note.media_items))
        )
        if note:
            await archive_note_media(db, note)
