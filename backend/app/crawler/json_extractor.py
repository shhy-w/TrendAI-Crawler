from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from app.crawler.types import CrawledMedia, CrawledPost


def extract_posts_from_x_json(payload: Any, keyword: str) -> list[CrawledPost]:
    posts: dict[str, CrawledPost] = {}
    for tweet in _walk_tweets(payload):
        post = _tweet_to_post(tweet, keyword)
        if post:
            posts[post.x_post_id] = post
    return list(posts.values())


def _walk_tweets(value: Any) -> list[dict[str, Any]]:
    tweets: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if _looks_like_tweet(value):
            tweets.append(value)
        for nested in value.values():
            tweets.extend(_walk_tweets(nested))
    elif isinstance(value, list):
        for item in value:
            tweets.extend(_walk_tweets(item))
    return tweets


def _looks_like_tweet(value: dict[str, Any]) -> bool:
    typename = value.get("__typename")
    legacy = value.get("legacy")
    rest_id = value.get("rest_id") or value.get("id_str")
    return bool(rest_id and isinstance(legacy, dict) and (typename in {None, "Tweet"} or "tweet" in str(typename).lower()))


def _tweet_to_post(tweet: dict[str, Any], keyword: str) -> CrawledPost | None:
    legacy = tweet.get("legacy")
    if not isinstance(legacy, dict):
        return None
    x_post_id = str(tweet.get("rest_id") or legacy.get("id_str") or "")
    text = legacy.get("full_text") or legacy.get("text") or ""
    if not x_post_id or not text:
        return None

    user = _extract_user(tweet)
    handle = user.get("screen_name")
    post_url = f"https://x.com/{handle or 'i'}/status/{x_post_id}"
    return CrawledPost(
        x_post_id=x_post_id,
        keyword=keyword,
        text=_clean_tweet_text(str(text)),
        author_name=user.get("name"),
        author_handle=handle,
        published_at=_parse_twitter_datetime(legacy.get("created_at")),
        post_url=post_url,
        reply_count=_safe_int(legacy.get("reply_count")),
        repost_count=_safe_int(legacy.get("retweet_count")),
        like_count=_safe_int(legacy.get("favorite_count")),
        view_count=_safe_int((tweet.get("views") or {}).get("count")),
        media_items=_extract_media(legacy),
    )


def _extract_user(tweet: dict[str, Any]) -> dict[str, str | None]:
    result = (((tweet.get("core") or {}).get("user_results") or {}).get("result") or {})
    legacy = result.get("legacy") or {}
    return {
        "name": legacy.get("name"),
        "screen_name": legacy.get("screen_name"),
    }


def _extract_media(legacy: dict[str, Any]) -> list[CrawledMedia]:
    entities = legacy.get("extended_entities") or legacy.get("entities") or {}
    raw_media = entities.get("media") or []
    media_items: list[CrawledMedia] = []
    for item in raw_media:
        media_type = item.get("type") or "image"
        media_url = _best_media_url(item)
        if not media_url:
            continue
        sizes = item.get("sizes") or {}
        large = sizes.get("large") or {}
        media_items.append(
            CrawledMedia(
                media_type="video" if media_type in {"video", "animated_gif"} else "image",
                media_url=media_url,
                thumbnail_url=item.get("media_url_https") or item.get("media_url"),
                width=_safe_optional_int(large.get("w")),
                height=_safe_optional_int(large.get("h")),
                sort_order=len(media_items),
            )
        )
    return media_items


def _best_media_url(item: dict[str, Any]) -> str | None:
    variants = (((item.get("video_info") or {}).get("variants")) or [])
    mp4_variants = [variant for variant in variants if variant.get("content_type") == "video/mp4" and variant.get("url")]
    if mp4_variants:
        best = max(mp4_variants, key=lambda variant: _safe_int(variant.get("bitrate")))
        return best.get("url")
    return item.get("media_url_https") or item.get("media_url")


def _clean_tweet_text(text: str) -> str:
    return text.replace("\u00a0", " ").strip()


def _parse_twitter_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(str(value))
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int:
    if value in {None, ""}:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_optional_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
