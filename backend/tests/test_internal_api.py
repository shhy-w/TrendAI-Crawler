import pytest

from app.crawler.internal_api import (
    InternalXApiCrawler,
    SearchOperation,
    SearchTimelineQueryNotFoundError,
    _extract_search_query_id,
    _extract_web_bearer,
)


class DummyClient:
    def __init__(self) -> None:
        self.headers = {"authorization": "Bearer test-web-token"}


def test_extract_web_bearer_from_script_authorization_literal() -> None:
    script = 'headers:{authorization:"Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAkPxtR8GyrDMwUeUGQ8QFw8FyH0U%3DCqHbxTnTn4j1nmrtuKqhoJkgS85FzJJGRwjiM5mT"}'

    assert _extract_web_bearer(script) == (
        "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAA"
        "kPxtR8GyrDMwUeUGQ8QFw8FyH0U%3D"
        "CqHbxTnTn4j1nmrtuKqhoJkgS85FzJJGRwjiM5mT"
    )


def test_extract_web_bearer_from_minified_script_literal() -> None:
    token = (
        "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAA"
        "kPxtR8GyrDMwUeUGQ8QFw8FyH0U%3D"
        "CqHbxTnTn4j1nmrtuKqhoJkgS85FzJJGRwjiM5mT"
    )

    assert _extract_web_bearer(f'a="{token}",b=1') == token


def test_extract_search_timeline_query_id_from_minified_operation_metadata() -> None:
    script = (
        '277523(e){e.exports={queryId:"Bcw3RzK-PatNAmbnw54hFw",'
        'operationName:"SearchTimeline",operationType:"query",metadata:{}}}'
    )

    assert _extract_search_query_id(script) == "Bcw3RzK-PatNAmbnw54hFw"


def test_extract_search_timeline_query_id_ignores_prefixed_operations() -> None:
    script = (
        '769303(e){e.exports={queryId:"I79RO1ZqoyWMPK1EST3FBw",'
        'operationName:"BookmarkSearchTimeline",operationType:"query",metadata:{}}}'
        '277523(e){e.exports={queryId:"Bcw3RzK-PatNAmbnw54hFw",'
        'operationName:"SearchTimeline",operationType:"query",metadata:{}}}'
    )

    assert _extract_search_query_id(script) == "Bcw3RzK-PatNAmbnw54hFw"


def test_extract_search_timeline_query_id_does_not_cross_previous_operation() -> None:
    script = (
        '111(e){e.exports={queryId:"Bcw3RzK-PatNAmbnw54hFw",'
        'operationName:"UserMedia",operationType:"query",metadata:{}}}'
        '222(e){e.exports={queryId:"QpNfg0kpPRfjROQ_9eOLXA",'
        'operationName:"SearchTimeline",operationType:"query",metadata:{}}}'
    )

    assert _extract_search_query_id(script) == "QpNfg0kpPRfjROQ_9eOLXA"


@pytest.mark.asyncio
async def test_search_via_relay_includes_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_headers = {}

    async def fake_search_via_relay(self, url, params, headers, allow_query_refresh=True):
        captured_headers.update(headers)
        return {"data": {}}

    monkeypatch.setattr(InternalXApiCrawler, "_search_via_relay", fake_search_via_relay)
    monkeypatch.setattr("app.crawler.internal_api.settings.x_relay_url", "http://relay.local")

    crawler = InternalXApiCrawler()
    await crawler._search(DummyClient(), SearchOperation("query-id"), "guest-token", "AI", 20)

    assert captured_headers["authorization"] == "Bearer test-web-token"
    assert captured_headers["x-guest-token"] == "guest-token"


@pytest.mark.asyncio
async def test_search_refreshes_query_id_when_relay_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    called_urls = []
    refresh_flags = []

    async def fake_search_via_relay(self, url, params, headers, allow_query_refresh=True):
        called_urls.append(url)
        if len(called_urls) == 1:
            raise SearchTimelineQueryNotFoundError("expired query id")
        return {"data": {"ok": True}}

    async def fake_get_search_operation(self, client, force_refresh=False):
        refresh_flags.append(force_refresh)
        return SearchOperation("fresh-query-id")

    monkeypatch.setattr(InternalXApiCrawler, "_search_via_relay", fake_search_via_relay)
    monkeypatch.setattr(InternalXApiCrawler, "_get_search_operation", fake_get_search_operation)
    monkeypatch.setattr("app.crawler.internal_api.settings.x_relay_url", "http://relay.local")

    crawler = InternalXApiCrawler()
    payload = await crawler._search(DummyClient(), SearchOperation("stale-query-id"), "guest-token", "AI", 20)

    assert payload == {"data": {"ok": True}}
    assert called_urls[0].endswith("/stale-query-id/SearchTimeline")
    assert called_urls[1].endswith("/fresh-query-id/SearchTimeline")
    assert refresh_flags == [True]
