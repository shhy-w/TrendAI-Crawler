import pytest

from app.crawler.errors import CrawlFailureType, classify_exception
from app.crawler.types import CrawledNote
from app.crawler.xhs_crawler import XHSCrawler, XHSNoContentError


def _note() -> CrawledNote:
    return CrawledNote(
        platform_note_id="note-1",
        note_type="normal",
        completeness="card",
        title="匿名卡片",
        content="",
        note_url="https://www.xiaohongshu.com/explore/note-1",
        author_id=None,
        author_name="作者",
        author_avatar=None,
        published_at=None,
    )


@pytest.mark.asyncio
async def test_auto_mode_returns_public_results_without_opening_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    crawler = XHSCrawler()
    authenticated_called = False

    async def public(source_type: str, target: str, limit: int):
        return [_note()]

    async def authenticated(source_type: str, target: str, limit: int):
        nonlocal authenticated_called
        authenticated_called = True
        return [_note()]

    monkeypatch.setattr(crawler, "_crawl_public", public)
    monkeypatch.setattr(crawler, "_crawl_authenticated", authenticated)

    notes = await crawler.crawl_source("keyword", "AI", 10, "auto")

    assert len(notes) == 1
    assert authenticated_called is False


@pytest.mark.asyncio
async def test_auto_mode_falls_back_to_authenticated_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    crawler = XHSCrawler()

    async def public(source_type: str, target: str, limit: int):
        raise XHSNoContentError("匿名无结果")

    async def authenticated(source_type: str, target: str, limit: int):
        return [_note()]

    monkeypatch.setattr(crawler, "_crawl_public", public)
    monkeypatch.setattr(crawler, "_crawl_authenticated", authenticated)

    notes = await crawler.crawl_source("keyword", "AI", 10, "auto")

    assert notes[0].platform_note_id == "note-1"


@pytest.mark.asyncio
async def test_public_mode_never_uses_authenticated_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    crawler = XHSCrawler()

    async def public(source_type: str, target: str, limit: int):
        return [_note()]

    async def authenticated(source_type: str, target: str, limit: int):
        raise AssertionError("登录通道不应执行")

    monkeypatch.setattr(crawler, "_crawl_public", public)
    monkeypatch.setattr(crawler, "_crawl_authenticated", authenticated)

    notes = await crawler.crawl_source("keyword", "AI", 10, "public")

    assert notes[0].completeness == "card"


def test_access_restriction_is_classified_separately() -> None:
    classified = classify_exception(RuntimeError("小红书限制了当前 IP 或网络环境"))
    assert classified.failure_type == CrawlFailureType.ACCESS_RESTRICTED
