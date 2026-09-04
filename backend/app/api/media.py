from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.media import Media
from app.services.media_archive_service import resolve_archived_media_path


router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{media_id}/content")
def get_media_content(media_id: int, db: Session = Depends(get_db)) -> FileResponse:
    media = db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    try:
        path = resolve_archived_media_path(media)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        path,
        media_type=media.mime_type or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=86400"},
    )
