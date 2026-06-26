from app.crawler.parser import build_crawled_post, parse_compact_count, parse_post_id


def test_parse_post_id() -> None:
    assert parse_post_id("https://x.com/openai/status/1234567890") == "1234567890"


def test_parse_compact_count() -> None:
    assert parse_compact_count("1.2K Likes") == 1200
    assert parse_compact_count("3万") == 30000
    assert parse_compact_count(None) == 0


def test_build_crawled_post_with_media() -> None:
    post = build_crawled_post(
        keyword="AI",
        post_url="https://x.com/user/status/42",
        text="AI agents are useful",
        author_name="User",
        author_blob="User\n@user\nAI agents are useful",
        published_at="2026-06-26T01:02:03.000Z",
        media_urls=["https://pbs.twimg.com/media/a.jpg"],
        metrics={"reply": "2", "repost": "3", "like": "4", "view": "5K"},
    )

    assert post is not None
    assert post.x_post_id == "42"
    assert post.author_handle == "user"
    assert post.view_count == 5000
    assert len(post.media_items) == 1
