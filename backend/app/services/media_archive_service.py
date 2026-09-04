from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.media import Media
from app.models.note import Note


ALLOWED_MEDIA_HOST_SUFFIXES = (".xhscdn.com", ".xiaohongshu.com")
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}


class MediaArchiveError(RuntimeError):
    pass


async def archive_note_media(db: Session, note: Note, force: bool = False) -> Note:
    if not settings.media_archive_enabled:
        return note
    settings.media_archive_path.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=60, headers={"referer": "https://www.xiaohongshu.com/"}) as client:
        for media in note.media_items:
            if not force and media.archive_status == "archived" and _resolved_local_path(media):
                continue
            await _archive_one(client, db, note, media)
    db.refresh(note)
    return note


async def _archive_one(client: httpx.AsyncClient, db: Session, note: Note, media: Media) -> None:
    media.archive_status = "archiving"
    media.archive_error = None
    db.commit()
    temp_path: Path | None = None
    response: httpx.Response | None = None
    try:
        response, final_url = await _open_validated_stream(client, media.media_url)
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if not _matches_media_type(media.media_type, content_type):
            raise MediaArchiveError(f"资源类型不匹配：{content_type or 'unknown'}")
        extension = CONTENT_TYPE_EXTENSIONS.get(content_type) or _url_extension(final_url, media.media_type)
        note_dir = settings.media_archive_path / note.platform_note_id
        note_dir.mkdir(parents=True, exist_ok=True)
        final_path = note_dir / f"{media.id}{extension}"
        temp_path = note_dir / f".{media.id}{extension}.part"
        max_bytes = settings.media_archive_video_max_bytes if media.media_type == "video" else settings.media_archive_image_max_bytes
        digest = hashlib.sha256()
        total = 0
        with temp_path.open("wb") as output:
            async for chunk in response.aiter_bytes(64 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise MediaArchiveError(f"资源超过归档上限 {max_bytes // (1024 * 1024)} MB")
                digest.update(chunk)
                output.write(chunk)
        temp_path.replace(final_path)
        if media.media_type == "image":
            with Image.open(final_path) as image:
                media.width, media.height = image.size
        media.local_path = str(final_path.relative_to(settings.media_archive_path))
        media.mime_type = content_type or None
        media.file_size = total
        media.checksum_sha256 = digest.hexdigest()
        media.archive_status = "archived"
        media.archive_error = None
        media.archived_at = datetime.now(timezone.utc)
    except Exception as exc:
        if temp_path and temp_path.exists():
            temp_path.unlink()
        media.archive_status = "failed"
        media.archive_error = str(exc)[:1024]
    finally:
        if response:
            await response.aclose()
    db.commit()


async def _open_validated_stream(
    client: httpx.AsyncClient,
    url: str,
    max_redirects: int = 4,
) -> tuple[httpx.Response, str]:
    current_url = url
    for _ in range(max_redirects + 1):
        _validate_media_url(current_url)
        request = client.build_request("GET", current_url)
        response = await client.send(request, stream=True)
        if response.is_redirect:
            location = response.headers.get("location")
            await response.aclose()
            if not location:
                raise MediaArchiveError("媒体重定向缺少目标地址")
            current_url = urljoin(current_url, location)
            continue
        try:
            response.raise_for_status()
        except Exception:
            await response.aclose()
            raise
        return response, current_url
    raise MediaArchiveError("媒体重定向次数过多")


def resolve_archived_media_path(media: Media) -> Path:
    path = _resolved_local_path(media)
    if not path or not path.is_file():
        raise FileNotFoundError("归档媒体不存在")
    return path


def _resolved_local_path(media: Media) -> Path | None:
    if not media.local_path:
        return None
    root = settings.media_archive_path.resolve()
    path = (root / media.local_path).resolve()
    if path != root and root not in path.parents:
        return None
    return path


def _validate_media_url(url: str) -> None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not any(hostname.endswith(suffix) for suffix in ALLOWED_MEDIA_HOST_SUFFIXES):
        raise MediaArchiveError("只允许归档小红书官方 HTTPS 媒体地址")


def _matches_media_type(media_type: str, content_type: str) -> bool:
    if media_type == "image":
        return content_type.startswith("image/")
    if media_type == "video":
        return content_type.startswith("video/")
    return False


def _url_extension(url: str, media_type: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm"}:
        return suffix
    return ".mp4" if media_type == "video" else ".bin"
