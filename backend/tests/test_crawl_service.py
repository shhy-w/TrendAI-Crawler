from app.crawler.types import CrawledMedia, CrawledPost
from app.models.post import Post
from app.services.crawl_service import create_crawl_job, upsert_posts


def test_create_crawl_job_normalizes_keywords(db_session) -> None:
    job = create_crawl_job(db_session, ["AI", " AI ", "agent"], 10)

    assert job.keywords == ["AI", "agent"]
    assert job.status == "pending"


def test_upsert_posts_updates_existing_and_replaces_media(db_session) -> None:
    first = CrawledPost(
        x_post_id="1",
        keyword="AI",
        text="old",
        author_name="A",
        author_handle="a",
        published_at=None,
        post_url="https://x.com/a/status/1",
        like_count=1,
        media_items=[CrawledMedia(media_type="image", media_url="https://example.com/1.jpg")],
    )
    second = CrawledPost(
        x_post_id="1",
        keyword="AI",
        text="new",
        author_name="A",
        author_handle="a",
        published_at=None,
        post_url="https://x.com/a/status/1",
        like_count=9,
        media_items=[CrawledMedia(media_type="image", media_url="https://example.com/2.jpg")],
    )

    assert upsert_posts(db_session, [first]) == 1
    assert upsert_posts(db_session, [second]) == 1

    posts = db_session.query(Post).all()
    assert len(posts) == 1
    assert posts[0].text == "new"
    assert posts[0].like_count == 9
    assert posts[0].media_items[0].media_url == "https://example.com/2.jpg"
