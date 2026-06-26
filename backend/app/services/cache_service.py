from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crawler.types import CrawledMedia, CrawledPost
from app.models.crawl_cache import CrawlCache


def search_cache_key(keyword: str, limit: int) -> str:
    return f"search:{keyword.strip().lower()}:{limit}"


def get_cached_posts(db: Session, keyword: str, limit: int) -> list[CrawledPost] | None:
    cache = db.scalar(select(CrawlCache).where(CrawlCache.cache_key == search_cache_key(keyword, limit)))
    if not cache:
        return None
    if cache.expires_at <= datetime.now(timezone.utc):
        db.delete(cache)
        db.commit()
        return None
    return [_post_from_payload(item) for item in cache.payload.get("posts", [])]


def set_cached_posts(db: Session, keyword: str, limit: int, posts: list[CrawledPost]) -> None:
    key = search_cache_key(keyword, limit)
    cache = db.scalar(select(CrawlCache).where(CrawlCache.cache_key == key))
    if cache is None:
        cache = CrawlCache(cache_key=key, payload={}, expires_at=datetime.now(timezone.utc))
        db.add(cache)
    cache.payload = {"posts": [_post_to_payload(post) for post in posts]}
    cache.expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.crawler_cache_ttl_seconds)
    db.commit()


def _post_to_payload(post: CrawledPost) -> dict:
    return {
        "x_post_id": post.x_post_id,
        "keyword": post.keyword,
        "text": post.text,
        "author_name": post.author_name,
        "author_handle": post.author_handle,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "post_url": post.post_url,
        "reply_count": post.reply_count,
        "repost_count": post.repost_count,
        "like_count": post.like_count,
        "view_count": post.view_count,
        "media_items": [
            {
                "media_type": media.media_type,
                "media_url": media.media_url,
                "thumbnail_url": media.thumbnail_url,
                "width": media.width,
                "height": media.height,
                "sort_order": media.sort_order,
            }
            for media in post.media_items
        ],
    }


def _post_from_payload(payload: dict) -> CrawledPost:
    published_at = payload.get("published_at")
    return CrawledPost(
        x_post_id=payload["x_post_id"],
        keyword=payload["keyword"],
        text=payload["text"],
        author_name=payload.get("author_name"),
        author_handle=payload.get("author_handle"),
        published_at=datetime.fromisoformat(published_at) if published_at else None,
        post_url=payload["post_url"],
        reply_count=payload.get("reply_count", 0),
        repost_count=payload.get("repost_count", 0),
        like_count=payload.get("like_count", 0),
        view_count=payload.get("view_count", 0),
        media_items=[
            CrawledMedia(
                media_type=media["media_type"],
                media_url=media["media_url"],
                thumbnail_url=media.get("thumbnail_url"),
                width=media.get("width"),
                height=media.get("height"),
                sort_order=media.get("sort_order", 0),
            )
            for media in payload.get("media_items", [])
        ],
    )
