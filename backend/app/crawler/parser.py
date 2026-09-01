from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlencode

from app.crawler.types import CrawledMedia, CrawledNote


NOTE_ID_RE = re.compile(r"/(?:explore|discovery/item)/([A-Za-z0-9]+)")
COUNT_RE = re.compile(r"([\d,.]+)\s*([KMB万亿]?)", re.IGNORECASE)


def parse_note_id(url: str) -> str | None:
    match = NOTE_ID_RE.search(url)
    return match.group(1) if match else None


def parse_compact_count(value: object) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    normalized = str(value).replace(",", "").strip()
    match = COUNT_RE.search(normalized)
    if not match:
        return 0
    number = float(match.group(1))
    suffix = match.group(2).upper()
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000, "万": 10_000, "亿": 100_000_000}.get(suffix, 1)
    return int(number * multiplier)


def parse_datetime(value: str | int | float | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def normalize_media(urls: list[tuple[str, str | None, int | None, int | None]]) -> list[CrawledMedia]:
    media_items: list[CrawledMedia] = []
    seen: set[str] = set()
    for url, thumbnail_url, width, height in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        media_type = "video" if "video" in url or ".mp4" in url else "image"
        media_items.append(CrawledMedia(media_type, url, thumbnail_url or (url if media_type == "image" else None), width, height, len(media_items)))
    return media_items


def extract_notes_from_payload(payload: object) -> list[CrawledNote]:
    notes: dict[str, CrawledNote] = {}

    def walk(value: object) -> None:
        if isinstance(value, dict):
            note_card = value.get("note_card") or value.get("noteCard")
            if isinstance(note_card, dict):
                note = build_crawled_note(note_card, value)
                if note:
                    notes[note.platform_note_id] = note
            elif _looks_like_note(value):
                note = build_crawled_note(value, value)
                if note:
                    notes[note.platform_note_id] = note
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    walk(payload)
    return list(notes.values())


def build_crawled_note(card: dict, envelope: dict | None = None) -> CrawledNote | None:
    envelope = envelope or card
    note_id = str(card.get("note_id") or card.get("noteId") or envelope.get("id") or "")
    if not note_id:
        return None
    user = card.get("user") if isinstance(card.get("user"), dict) else {}
    interact = card.get("interact_info") if isinstance(card.get("interact_info"), dict) else {}
    token = envelope.get("xsec_token") or envelope.get("xsecToken")
    note_url = f"https://www.xiaohongshu.com/explore/{note_id}"
    if token:
        note_url = f"{note_url}?{urlencode({'xsec_token': str(token), 'xsec_source': 'pc_search'})}"

    media_values: list[tuple[str, str | None, int | None, int | None]] = []
    for image in card.get("image_list") or card.get("imageList") or []:
        if not isinstance(image, dict):
            continue
        url = _image_url(image)
        if url:
            media_values.append((url, url, _safe_int(image.get("width")) or None, _safe_int(image.get("height")) or None))
    video_url, video_cover = _video_urls(card.get("video"))
    if video_url:
        media_values.append((video_url, video_cover, None, None))
    if not media_values:
        cover = card.get("cover") if isinstance(card.get("cover"), dict) else {}
        cover_url = _image_url(cover)
        if cover_url:
            media_values.append((cover_url, cover_url, _safe_int(cover.get("width")) or None, _safe_int(cover.get("height")) or None))

    return CrawledNote(
        platform_note_id=note_id,
        note_type=str(card.get("type") or "normal"),
        title=str(card.get("title") or card.get("display_title") or "").strip(),
        content=str(card.get("desc") or card.get("content") or "").strip(),
        note_url=note_url,
        author_id=_optional_string(user.get("user_id") or user.get("userId")),
        author_name=_optional_string(user.get("nickname") or user.get("nick_name")),
        author_avatar=_optional_string(user.get("avatar")),
        published_at=parse_datetime(card.get("time") or card.get("publish_time")),
        ip_location=_optional_string(card.get("ip_location")),
        like_count=parse_compact_count(interact.get("liked_count") or interact.get("like_count")),
        collect_count=parse_compact_count(interact.get("collected_count") or interact.get("collect_count")),
        comment_count=parse_compact_count(interact.get("comment_count")),
        share_count=parse_compact_count(interact.get("share_count") or interact.get("shared_count")),
        media_items=normalize_media(media_values),
        raw_data=card,
    )


def _looks_like_note(value: dict) -> bool:
    return bool((value.get("note_id") or value.get("noteId")) and (value.get("user") or value.get("interact_info") or value.get("image_list")))


def _image_url(image: dict) -> str | None:
    for key in ("url_default", "url_pre", "url"):
        value = image.get(key)
        if isinstance(value, str) and value.startswith("http"):
            return value
    for info in image.get("info_list") or []:
        if isinstance(info, dict) and isinstance(info.get("url"), str) and info["url"].startswith("http"):
            return info["url"]
    return None


def _video_urls(video: object) -> tuple[str | None, str | None]:
    if not isinstance(video, dict):
        return None, None
    image = video.get("image")
    cover = _image_url(image) if isinstance(image, dict) else None
    stack: list[object] = [video]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            for key, nested in value.items():
                if key in {"master_url", "backup_url", "url"} and isinstance(nested, str) and nested.startswith("http"):
                    return nested, cover
                stack.append(nested)
        elif isinstance(value, list):
            stack.extend(value)
    return None, cover


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _optional_string(value: object) -> str | None:
    return str(value).strip() if value is not None and str(value).strip() else None
