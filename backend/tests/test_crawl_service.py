from sqlalchemy import select

from app.crawler.types import CrawledMedia, CrawledNote
from app.models.note import Note
from app.models.note_source import NoteSource
from app.models.source import Source
from app.services.crawl_service import create_crawl_job, upsert_notes


def _note(title: str, media_url: str) -> CrawledNote:
    return CrawledNote(
        platform_note_id="note-1",
        note_type="normal",
        completeness="complete",
        title=title,
        content="正文",
        note_url="https://www.xiaohongshu.com/explore/note-1",
        author_id="author-1",
        author_name="作者",
        author_avatar=None,
        published_at=None,
        like_count=12,
        collect_count=3,
        media_items=[CrawledMedia(media_type="image", media_url=media_url)],
    )


def test_create_crawl_job_builds_source_items(db_session) -> None:
    source = Source(name="AI 工具", source_type="keyword", target="AI 工具", enabled=True)
    db_session.add(source)
    db_session.commit()

    job = create_crawl_job(db_session, [source.id], 10, "public")

    assert job.status == "pending"
    assert job.crawl_mode == "public"
    assert job.total_sources == 1
    assert job.items[0].source_name == "AI 工具"


def test_upsert_notes_updates_content_and_tracks_multiple_sources(db_session) -> None:
    source_a = Source(name="AI", source_type="keyword", target="AI", enabled=True)
    source_b = Source(name="效率", source_type="keyword", target="效率", enabled=True)
    db_session.add_all([source_a, source_b])
    db_session.commit()

    assert upsert_notes(db_session, [_note("旧标题", "https://img.example/1.jpg")], source_a) == 1
    assert upsert_notes(db_session, [_note("新标题", "https://img.example/2.jpg")], source_b) == 1

    note = db_session.scalar(select(Note))
    assert note is not None
    assert note.title == "新标题"
    assert note.completeness == "complete"
    assert note.media_items[0].media_url == "https://img.example/2.jpg"
    assert db_session.query(NoteSource).count() == 2
    assert len(note.metric_snapshots) == 2


def test_upsert_notes_does_not_replace_archived_original_with_preview(db_session) -> None:
    original = _note("原图", "https://img.example/original.jpg")
    original.media_items[0].quality = "original"
    original.media_items[0].width = 2160
    original.media_items[0].height = 2880
    upsert_notes(db_session, [original], source=None)

    note = db_session.scalar(select(Note))
    media = note.media_items[0]
    original_media_id = media.id
    media.archive_status = "archived"
    media.local_path = "note-1/original.jpg"
    media.file_size = 1024
    db_session.commit()

    preview = _note("预览", "https://img.example/preview.jpg")
    preview.completeness = "card"
    preview.media_items[0].quality = "preview"
    preview.media_items[0].width = 540
    preview.media_items[0].height = 720
    upsert_notes(db_session, [preview], source=None)

    db_session.expire_all()
    note = db_session.scalar(select(Note))
    assert len(note.media_items) == 1
    assert note.media_items[0].id == original_media_id
    assert note.media_items[0].media_url.endswith("original.jpg")
    assert note.media_items[0].quality == "original"
    assert note.media_items[0].archive_status == "archived"
    assert note.media_items[0].width == 2160
    assert note.media_items[0].height == 2880


def test_upsert_notes_promotes_preview_to_original(db_session) -> None:
    preview = _note("预览", "https://img.example/preview.jpg")
    preview.media_items[0].width = 540
    preview.media_items[0].height = 720
    upsert_notes(db_session, [preview], source=None)

    note = db_session.scalar(select(Note))
    media = note.media_items[0]
    media.archive_status = "archived"
    media.local_path = "note-1/preview.jpg"
    db_session.commit()

    original = _note("原图", "https://img.example/original.jpg")
    original.media_items[0].quality = "original"
    original.media_items[0].width = 2160
    original.media_items[0].height = 2880
    upsert_notes(db_session, [original], source=None)

    db_session.expire_all()
    note = db_session.scalar(select(Note))
    assert len(note.media_items) == 1
    assert note.media_items[0].media_url.endswith("original.jpg")
    assert note.media_items[0].quality == "original"
    assert note.media_items[0].archive_status == "remote"
    assert note.media_items[0].local_path is None
    assert note.media_items[0].width == 2160
    assert note.media_items[0].height == 2880


def test_upsert_notes_keeps_full_original_carousel_after_single_preview(db_session) -> None:
    original = _note("原图组", "https://img.example/original-1.jpg")
    original.media_items[0].quality = "original"
    original.media_items.append(
        CrawledMedia(
            media_type="image",
            media_url="https://img.example/original-2.jpg",
            width=2160,
            height=2880,
            sort_order=1,
            quality="original",
        )
    )
    upsert_notes(db_session, [original], source=None)

    preview = _note("预览", "https://img.example/preview.jpg")
    preview.completeness = "card"
    upsert_notes(db_session, [preview], source=None)

    db_session.expire_all()
    note = db_session.scalar(select(Note))
    assert [media.media_url for media in note.media_items] == [
        "https://img.example/original-1.jpg",
        "https://img.example/original-2.jpg",
    ]
