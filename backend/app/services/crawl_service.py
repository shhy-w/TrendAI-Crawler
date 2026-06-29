from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.crawler.errors import CrawlFailureType, classify_exception
from app.crawler.x_crawler import XCrawler
from app.db.session import SessionLocal
from app.models.crawl_failure import CrawlFailure
from app.models.crawl_job import CrawlJob, CrawlJobStatus
from app.models.media import Media
from app.models.post import Post
from app.crawler.types import CrawledPost
from app.services.cache_service import get_cached_posts, set_cached_posts
from app.services.proxy_service import choose_proxy, mark_proxy_failure, mark_proxy_success


def create_crawl_job(db: Session, keywords: list[str], max_posts_per_keyword: int) -> CrawlJob:
    normalized_keywords = sorted({keyword.strip() for keyword in keywords if keyword.strip()})
    job = CrawlJob(
        status=CrawlJobStatus.PENDING.value,
        keywords=normalized_keywords,
        max_posts_per_keyword=max_posts_per_keyword,
        success_count=0,
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
        job = db.get(CrawlJob, job_id)
        if not job:
            return
        job.status = CrawlJobStatus.RUNNING.value
        job.started_at = datetime.now(timezone.utc)
        job.failure_type = None
        job.debug_path = None
        job.error_message = None
        db.commit()

        proxy = choose_proxy(db)
        crawler = XCrawler(proxy_url=proxy.proxy_url if proxy else None, db=db, proxy_id=proxy.id if proxy else None)
        total_saved = 0
        for keyword in job.keywords:
            crawled_posts = get_cached_posts(db, keyword, job.max_posts_per_keyword)
            if crawled_posts is None:
                crawled_posts = await crawler.crawl_keyword(keyword, job.max_posts_per_keyword)
                set_cached_posts(db, keyword, job.max_posts_per_keyword, crawled_posts)
            total_saved += upsert_posts(db, crawled_posts)
        mark_proxy_success(db, proxy)

        job.status = CrawlJobStatus.SUCCEEDED.value
        job.success_count = total_saved
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(CrawlJob, job_id)
        if job:
            classified = classify_exception(exc)
            job.status = CrawlJobStatus.FAILED.value
            job.failure_type = classified.failure_type
            job.debug_path = classified.debug_path
            job.error_message = classified.message
            job.finished_at = datetime.now(timezone.utc)
            db.add(
                CrawlFailure(
                    job_id=job.id,
                    keyword=",".join(job.keywords),
                    failure_type=classified.failure_type,
                    message=classified.message,
                    debug_path=classified.debug_path,
                    proxy_id=proxy.id if "proxy" in locals() and proxy else None,
                )
            )
            db.commit()
            if classified.failure_type in {
                CrawlFailureType.NETWORK,
                CrawlFailureType.RATE_LIMITED,
                CrawlFailureType.GUEST_TOKEN_DENIED,
            }:
                mark_proxy_failure(db, proxy if "proxy" in locals() else None, classified.message)
    finally:
        db.close()


def upsert_posts(db: Session, crawled_posts: list[CrawledPost]) -> int:
    saved = 0
    for crawled in crawled_posts:
        post = db.scalar(
            select(Post)
            .where(Post.x_post_id == crawled.x_post_id)
            .options(selectinload(Post.media_items))
        )
        if post is None:
            post = Post(x_post_id=crawled.x_post_id)
            db.add(post)
        post.keyword = crawled.keyword
        post.text = crawled.text
        post.author_name = crawled.author_name
        post.author_handle = crawled.author_handle
        post.published_at = crawled.published_at
        post.post_url = crawled.post_url
        post.reply_count = crawled.reply_count
        post.repost_count = crawled.repost_count
        post.like_count = crawled.like_count
        post.view_count = crawled.view_count
        post.crawled_at = datetime.now(timezone.utc)
        db.flush()

        db.execute(delete(Media).where(Media.post_id == post.id))
        for media in crawled.media_items:
            db.add(
                Media(
                    post_id=post.id,
                    media_type=media.media_type,
                    media_url=media.media_url,
                    thumbnail_url=media.thumbnail_url,
                    width=media.width,
                    height=media.height,
                    sort_order=media.sort_order,
                )
            )
        saved += 1
    db.commit()
    return saved
