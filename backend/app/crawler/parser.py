from __future__ import annotations

import re
from datetime import datetime

from app.crawler.types import CrawledMedia, CrawledPost

POST_ID_RE = re.compile(r"/status/(\d+)")
HANDLE_RE = re.compile(r"@([A-Za-z0-9_]{1,15})")
COUNT_RE = re.compile(r"([\d,.]+)\s*([KMB万亿]?)", re.IGNORECASE)


def parse_post_id(url: str) -> str | None:
    match = POST_ID_RE.search(url)
    return match.group(1) if match else None


def parse_compact_count(value: str | None) -> int:
    if not value:
        return 0
    normalized = value.replace(",", "").strip()
    match = COUNT_RE.search(normalized)
    if not match:
        return 0
    number = float(match.group(1))
    suffix = match.group(2).upper()
    multiplier = {
        "K": 1_000,
        "M": 1_000_000,
        "B": 1_000_000_000,
        "万": 10_000,
        "亿": 100_000_000,
    }.get(suffix, 1)
    return int(number * multiplier)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_handle(text: str | None) -> str | None:
    if not text:
        return None
    match = HANDLE_RE.search(text)
    return match.group(1) if match else None


def normalize_media(urls: list[str]) -> list[CrawledMedia]:
    media_items: list[CrawledMedia] = []
    seen: set[str] = set()
    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        media_type = "video" if "video" in url or ".mp4" in url else "image"
        media_items.append(
            CrawledMedia(
                media_type=media_type,
                media_url=url,
                thumbnail_url=url if media_type == "image" else None,
                sort_order=len(media_items),
            )
        )
    return media_items


def build_crawled_post(
    *,
    keyword: str,
    post_url: str,
    text: str,
    author_name: str | None,
    author_blob: str | None,
    published_at: str | None,
    media_urls: list[str],
    metrics: dict[str, str | None],
) -> CrawledPost | None:
    x_post_id = parse_post_id(post_url)
    if not x_post_id or not text.strip():
        return None
    return CrawledPost(
        x_post_id=x_post_id,
        keyword=keyword,
        text=text.strip(),
        author_name=author_name,
        author_handle=extract_handle(author_blob),
        published_at=parse_datetime(published_at),
        post_url=post_url,
        reply_count=parse_compact_count(metrics.get("reply")),
        repost_count=parse_compact_count(metrics.get("repost")),
        like_count=parse_compact_count(metrics.get("like")),
        view_count=parse_compact_count(metrics.get("view")),
        media_items=normalize_media(media_urls),
    )
