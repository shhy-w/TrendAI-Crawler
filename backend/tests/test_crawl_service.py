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

    job = create_crawl_job(db_session, [source.id], 10)

    assert job.status == "pending"
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
    assert note.media_items[0].media_url == "https://img.example/2.jpg"
    assert db_session.query(NoteSource).count() == 2
    assert len(note.metric_snapshots) == 2
