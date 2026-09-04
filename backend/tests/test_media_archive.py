import base64

import httpx
import pytest

from app.models.media import Media
from app.models.note import Note
from app.services.media_archive_service import archive_note_media, resolve_archived_media_path


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@pytest.mark.asyncio
async def test_archive_image_records_file_metadata(db_session, monkeypatch, tmp_path) -> None:
    note = Note(platform_note_id="note-archive", title="归档", content="", note_url="https://www.xiaohongshu.com/explore/note-archive")
    note.media_items.append(Media(media_type="image", media_url="https://sns-webpic-qc.xhscdn.com/image.png", quality="original"))
    db_session.add(note)
    db_session.commit()
    monkeypatch.setattr("app.services.media_archive_service.settings.media_archive_dir", str(tmp_path))

    async def fake_stream(client, url):
        request = httpx.Request("GET", url)
        return httpx.Response(200, headers={"content-type": "image/png"}, content=PNG_1X1, request=request), url

    monkeypatch.setattr("app.services.media_archive_service._open_validated_stream", fake_stream)

    await archive_note_media(db_session, note)

    media = note.media_items[0]
    assert media.archive_status == "archived"
    assert media.mime_type == "image/png"
    assert media.width == 1
    assert media.height == 1
    assert media.file_size == len(PNG_1X1)
    assert resolve_archived_media_path(media).is_file()
    assert resolve_archived_media_path(media).read_bytes() == PNG_1X1
    assert media.content_url == f"/api/media/{media.id}/content"
