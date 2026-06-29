from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crawler.json_extractor import extract_posts_from_x_json
from app.crawler.types import CrawledPost
from app.models.guest_token import GuestToken
from app.models.web_bearer_token import WebBearerToken
from app.services.token_service import (
    get_active_guest_token,
    get_active_web_bearer_token,
    get_query_id,
    mark_guest_token_failed,
    mark_web_bearer_token_failed,
    store_guest_token,
    store_query_id,
    store_web_bearer_token,
)

WEB_BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAA"
    "kPxtR8GyrDMwUeUGQ8QFw8FyH0U%3D"
    "CqHbxTnTn4j1nmrtuKqhoJkgS85FzJJGRwjiM5mT"
)

SEARCH_OPERATION_RE = re.compile(
    r"(?:queryId|queryId\\\")\s*[:=]\s*[\"'](?P<query_id>[A-Za-z0-9_-]{20,})[\"']"
    r".{0,500}?"
    r"(?:operationName|operationName\\\")\s*[:=]\s*[\"']SearchTimeline[\"']",
    re.DOTALL,
)
SEARCH_OPERATION_RE_REVERSED = re.compile(
    r"(?:operationName|operationName\\\")\s*[:=]\s*[\"']SearchTimeline[\"']"
    r".{0,500}?"
    r"(?:queryId|queryId\\\")\s*[:=]\s*[\"'](?P<query_id>[A-Za-z0-9_-]{20,})[\"']",
    re.DOTALL,
)
SEARCH_OPERATION_NAME_RE = re.compile(r"(?:operationName|operationName\\\")\s*[:=]\s*[\"']SearchTimeline[\"']")
QUERY_ID_RE = re.compile(r"(?:queryId|queryId\\\")\s*[:=]\s*[\"'](?P<query_id>[A-Za-z0-9_-]{20,})[\"']")
SCRIPT_RE = re.compile(r"<script[^>]+src=[\"'](?P<src>https://abs\.twimg\.com/[^\"']+\.js)[\"']")
WEB_BEARER_RE = re.compile(r"Bearer\s+(?P<token>AAAAAAAAAAAAAAAAAAAAA[A-Za-z0-9%_-]{60,})")
WEB_BEARER_LITERAL_RE = re.compile(r"(?P<token>AAAAAAAAAAAAAAAAAAAAA[A-Za-z0-9%_-]{60,})")
KNOWN_WEB_SCRIPT_URLS = (
    "https://abs.twimg.com/responsive-web/client-web/main.15b2a66a.js",
)


class InternalXApiError(RuntimeError):
    pass


class SearchTimelineQueryNotFoundError(InternalXApiError):
    pass


@dataclass(frozen=True)
class SearchOperation:
    query_id: str


@dataclass(frozen=True)
class WebBearer:
    token: str
    source_url: str | None


class InternalXApiCrawler:
    def __init__(self, proxy_url: str | None = None, db: Session | None = None, proxy_id: int | None = None) -> None:
        self._operation: SearchOperation | None = None
        self.proxy_url = proxy_url
        self.db = db
        self.proxy_id = proxy_id

    async def crawl_keyword(self, keyword: str, limit: int) -> list[CrawledPost]:
        token_record: GuestToken | None = None
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(25.0, connect=10.0),
            follow_redirects=True,
            proxies=self.proxy_url,
            headers={
                "user-agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/130.0.0.0 Safari/537.36"
                ),
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "origin": "https://twitter.com",
                "referer": "https://twitter.com/",
            },
        ) as client:
            bearer_record = await self._ensure_web_bearer(client)
            client.headers["authorization"] = f"Bearer {bearer_record.token if bearer_record else WEB_BEARER_TOKEN}"
            if self.db and not settings.x_relay_url:
                token_record = get_active_guest_token(self.db, self.proxy_id)
            guest_token = token_record.guest_token if token_record else await self._activate_guest(client)
            if self.db and token_record is None and not settings.x_relay_url:
                token_record = store_guest_token(self.db, self.proxy_id, guest_token)
            operation = await self._get_search_operation(client)
            try:
                payload = await self._search(client, operation, guest_token, keyword, limit)
            except InternalXApiError as exc:
                if self.db:
                    mark_guest_token_failed(self.db, token_record, str(exc))
                raise
        posts = extract_posts_from_x_json(payload, keyword)[:limit]
        if not posts:
            raise InternalXApiError("SearchTimeline 响应中未解析到帖子")
        return posts

    async def _activate_guest(self, client: httpx.AsyncClient) -> str:
        response = await self._activate_guest_response(client)
        if response.status_code in {401, 403}:
            bearer_record = await self._ensure_web_bearer(client, force_refresh=True)
            if bearer_record:
                client.headers["authorization"] = f"Bearer {bearer_record.token}"
                response = await self._activate_guest_response(client)
                if response.status_code in {401, 403} and self.db:
                    mark_web_bearer_token_failed(self.db, bearer_record, f"guest token 获取失败：HTTP {response.status_code}")
        if response.status_code >= 400:
            raise InternalXApiError(f"guest token 获取失败：HTTP {response.status_code} {response.text[:200]}")
        token = response.json().get("guest_token")
        if not token:
            raise InternalXApiError("guest token 响应中没有 guest_token")
        return str(token)

    async def _activate_guest_response(self, client: httpx.AsyncClient) -> httpx.Response:
        if settings.x_relay_url:
            return await self._relay_request_json_response(
                "POST",
                "https://api.twitter.com/1.1/guest/activate.json",
                params={},
                headers={"authorization": str(client.headers.get("authorization", f"Bearer {WEB_BEARER_TOKEN}"))},
                json_body={},
            )
        return await client.post("https://api.twitter.com/1.1/guest/activate.json")

    async def _ensure_web_bearer(self, client: httpx.AsyncClient, force_refresh: bool = False) -> WebBearerToken | WebBearer | None:
        if self.db and not force_refresh:
            cached = get_active_web_bearer_token(self.db)
            if cached:
                return cached
        token, source_url = await self._discover_web_bearer(client)
        if self.db:
            return store_web_bearer_token(self.db, token, source_url)
        return WebBearer(token=token, source_url=source_url)

    async def _discover_web_bearer(self, client: httpx.AsyncClient) -> tuple[str, str | None]:
        entry_text = ""
        for entry_url in ("https://twitter.com/", "https://x.com/"):
            try:
                entry_text = await self._get_text(client, entry_url)
            except httpx.HTTPError:
                continue
            if entry_text:
                break
        script_urls = [match.group("src") for match in SCRIPT_RE.finditer(entry_text)]
        prioritized = [*KNOWN_WEB_SCRIPT_URLS, *sorted(script_urls, key=lambda url: ("main" not in url and "vendor" not in url, url))]
        seen: set[str] = set()
        for script_url in prioritized[:32]:
            if script_url in seen:
                continue
            seen.add(script_url)
            try:
                script_text = await self._get_text(client, urljoin("https://x.com/", script_url))
            except httpx.HTTPError:
                continue
            token = _extract_web_bearer(script_text)
            if token:
                return token, script_url
        token = _extract_web_bearer(entry_text)
        if token:
            return token, "https://x.com/"
        raise InternalXApiError("未能从 X 前端脚本中发现 Web Bearer")

    async def _get_search_operation(self, client: httpx.AsyncClient, force_refresh: bool = False) -> SearchOperation:
        if self._operation and not force_refresh:
            return self._operation
        if self.db and not force_refresh:
            cached = get_query_id(self.db, "SearchTimeline")
            if cached:
                self._operation = SearchOperation(query_id=cached.query_id)
                return self._operation
        entry_text = ""
        for entry_url in ("https://twitter.com/", "https://x.com/"):
            try:
                entry_text = await self._get_text(client, entry_url)
            except httpx.HTTPError:
                continue
            if entry_text:
                break
        script_urls = [match.group("src") for match in SCRIPT_RE.finditer(entry_text)]
        discovered_urls = sorted(script_urls, key=lambda url: ("Search" not in url and "Routes" not in url, url))
        prioritized = [*discovered_urls, *KNOWN_WEB_SCRIPT_URLS] if force_refresh else [*KNOWN_WEB_SCRIPT_URLS, *discovered_urls]
        seen: set[str] = set()
        checked_urls: list[str] = []
        for script_url in prioritized[:24]:
            if script_url in seen:
                continue
            seen.add(script_url)
            checked_urls.append(script_url)
            try:
                script_text = await self._get_text(client, urljoin("https://x.com/", script_url))
            except httpx.HTTPError:
                continue
            query_id = _extract_search_query_id(script_text)
            if query_id:
                self._operation = SearchOperation(query_id=query_id)
                if self.db:
                    store_query_id(self.db, "SearchTimeline", query_id, script_url)
                return self._operation
        raise InternalXApiError(
            "未能从 X 前端脚本中发现 SearchTimeline queryId，"
            f"已检查 {len(checked_urls)} 个脚本：{', '.join(checked_urls[:5])}"
        )

    async def _get_text(self, client: httpx.AsyncClient, url: str) -> str:
        if settings.x_relay_url and urlparse(url).hostname in {"x.com", "twitter.com", "abs.twimg.com"}:
            return await self._get_text_via_relay(url)
        return await _get_text_with_retries(client, url)

    async def _get_text_via_relay(self, url: str) -> str:
        response = await self._relay_request_json_response(
            "GET",
            url,
            params={},
            headers={},
            json_body=None,
            response_type="text",
            timeout=45.0,
        )
        if response.status_code >= 400:
            raise InternalXApiError(f"relay 文本请求失败：HTTP {response.status_code} {response.text[:200]}")
        payload = response.json()
        return str(payload.get("text", ""))

    async def _search(
        self,
        client: httpx.AsyncClient,
        operation: SearchOperation,
        guest_token: str,
        keyword: str,
        limit: int,
    ) -> Any:
        variables = {
            "rawQuery": keyword,
            "count": max(limit, 20),
            "querySource": "typed_query",
            "product": "Top",
        }
        features = _default_features()
        params = {
            "variables": json.dumps(variables, separators=(",", ":")),
            "features": json.dumps(features, separators=(",", ":")),
        }
        headers = {
            "authorization": str(client.headers.get("authorization", f"Bearer {WEB_BEARER_TOKEN}")),
            "x-guest-token": guest_token,
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
        }
        url = f"https://x.com/i/api/graphql/{operation.query_id}/SearchTimeline"
        if settings.x_relay_url:
            try:
                return await self._search_via_relay(url, params, headers)
            except SearchTimelineQueryNotFoundError:
                refreshed_operation = await self._get_search_operation(client, force_refresh=True)
                refreshed_url = f"https://x.com/i/api/graphql/{refreshed_operation.query_id}/SearchTimeline"
                return await self._search_via_relay(refreshed_url, params, headers, allow_query_refresh=False)
        response = await client.get(url, params=params, headers=headers)
        if response.status_code == 404:
            refreshed_operation = await self._get_search_operation(client, force_refresh=True)
            refreshed_url = f"https://x.com/i/api/graphql/{refreshed_operation.query_id}/SearchTimeline"
            response = await client.get(refreshed_url, params=params, headers=headers)
        if response.status_code >= 400:
            raise InternalXApiError(f"SearchTimeline 请求失败：HTTP {response.status_code} {response.text[:200]}")
        return response.json()

    async def _search_via_relay(
        self,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        allow_query_refresh: bool = True,
    ) -> Any:
        response = await self._relay_request_json_response("GET", url, params=params, headers=headers)
        if response.status_code == 404 and allow_query_refresh:
            raise SearchTimelineQueryNotFoundError("SearchTimeline queryId 已失效")
        if response.status_code >= 400:
            raise InternalXApiError(f"relay SearchTimeline 请求失败：HTTP {response.status_code} {response.text[:200]}")
        return response.json()

    async def _relay_request_json_response(
        self,
        method: str,
        url: str,
        params: dict[str, str],
        headers: dict[str, str],
        json_body: dict[str, Any] | None = None,
        response_type: str = "json",
        timeout: float = 35.0,
    ) -> httpx.Response:
        relay_headers = {"content-type": "application/json"}
        if settings.x_relay_token:
            relay_headers["x-relay-token"] = settings.x_relay_token
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as relay_client:
            return await relay_client.post(
                settings.x_relay_url.rstrip("/") + "/fetch",
                json={
                    "method": method,
                    "url": url,
                    "params": params,
                    "headers": headers,
                    "json_body": json_body,
                    "response_type": response_type,
                },
                headers=relay_headers,
            )


def _extract_search_query_id(script: str) -> str | None:
    for operation_match in SEARCH_OPERATION_NAME_RE.finditer(script):
        object_start = script.rfind("e.exports={", 0, operation_match.start())
        if object_start != -1:
            object_end = script.find("}}}", operation_match.end())
            if object_end == -1:
                object_end = script.find("})", operation_match.end())
            object_text = script[object_start : object_end if object_end != -1 else operation_match.end() + 500]
            query_match = QUERY_ID_RE.search(object_text)
            if query_match:
                return query_match.group("query_id")
    for pattern in (SEARCH_OPERATION_RE, SEARCH_OPERATION_RE_REVERSED):
        match = pattern.search(script)
        if match:
            return match.group("query_id")
    return None


def _extract_web_bearer(script: str) -> str | None:
    for pattern in (WEB_BEARER_RE, WEB_BEARER_LITERAL_RE):
        match = pattern.search(script)
        if match:
            return match.group("token")
    return None


async def _get_text_with_retries(client: httpx.AsyncClient, url: str, attempts: int = 3) -> str:
    last_exc: httpx.HTTPError | None = None
    for current_client in (client, None):
        for _ in range(attempts):
            try:
                if current_client is None:
                    async with httpx.AsyncClient(
                        timeout=httpx.Timeout(25.0, connect=10.0),
                        headers={"user-agent": client.headers.get("user-agent", "Mozilla/5.0")},
                    ) as direct_client:
                        response = await direct_client.get(url)
                else:
                    response = await current_client.get(url)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as exc:
                last_exc = exc
    if last_exc:
        raise last_exc
    raise InternalXApiError(f"请求脚本失败：{url}")


def _default_features() -> dict[str, bool]:
    return {
        "rweb_video_screen_enabled": False,
        "payments_enabled": False,
        "profile_label_improvements_pcf_label_in_post_enabled": True,
        "rweb_tipjar_consumption_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "premium_content_api_read_enabled": False,
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
        "responsive_web_grok_analyze_post_followups_enabled": False,
        "responsive_web_jetfuel_frame": False,
        "responsive_web_grok_share_attachment_enabled": False,
        "articles_preview_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "responsive_web_grok_show_grok_translated_post": False,
        "responsive_web_grok_analysis_button_from_backend": False,
        "creator_subscriptions_quote_tweet_preview_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_grok_image_annotation_enabled": False,
        "responsive_web_enhance_cards_enabled": False,
    }
