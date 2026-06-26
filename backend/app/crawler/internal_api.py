from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy.orm import Session

from app.crawler.json_extractor import extract_posts_from_x_json
from app.crawler.types import CrawledPost
from app.models.guest_token import GuestToken
from app.services.token_service import get_active_guest_token, get_query_id, mark_guest_token_failed, store_guest_token, store_query_id

WEB_BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAA"
    "kPxtR8GyrDMwUeUGQ8QFw8FyH0U%3D"
    "CqHbxTnTn4j1nmrtuKqhoJkgS85FzJJGRwjiM5mT"
)

SEARCH_OPERATION_RE = re.compile(
    r"(?:queryId|queryId\\\")\\s*[:=]\\s*[\"'](?P<query_id>[A-Za-z0-9_-]{20,})[\"']"
    r".{0,800}?"
    r"(?:operationName|operationName\\\")\\s*[:=]\\s*[\"']SearchTimeline[\"']",
    re.DOTALL,
)
SEARCH_OPERATION_RE_REVERSED = re.compile(
    r"(?:operationName|operationName\\\")\\s*[:=]\\s*[\"']SearchTimeline[\"']"
    r".{0,800}?"
    r"(?:queryId|queryId\\\")\\s*[:=]\\s*[\"'](?P<query_id>[A-Za-z0-9_-]{20,})[\"']",
    re.DOTALL,
)
SCRIPT_RE = re.compile(r"<script[^>]+src=[\"'](?P<src>https://abs\\.twimg\\.com/[^\"']+\\.js)[\"']")


class InternalXApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class SearchOperation:
    query_id: str


class InternalXApiCrawler:
    def __init__(self, proxy_url: str | None = None, db: Session | None = None, proxy_id: int | None = None) -> None:
        self._operation: SearchOperation | None = None
        self.proxy_url = proxy_url
        self.db = db
        self.proxy_id = proxy_id

    async def crawl_keyword(self, keyword: str, limit: int) -> list[CrawledPost]:
        token_record: GuestToken | None = None
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(12.0, connect=8.0),
            follow_redirects=True,
            proxies=self.proxy_url,
            headers={
                "authorization": f"Bearer {WEB_BEARER_TOKEN}",
                "user-agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/130.0.0.0 Safari/537.36"
                ),
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "origin": "https://x.com",
                "referer": "https://x.com/",
            },
        ) as client:
            if self.db:
                token_record = get_active_guest_token(self.db, self.proxy_id)
            guest_token = token_record.guest_token if token_record else await self._activate_guest(client)
            if self.db and token_record is None:
                token_record = store_guest_token(self.db, self.proxy_id, guest_token)
            operation = await self._get_search_operation(client)
            try:
                payload = await self._search(client, operation, guest_token, keyword, limit)
            except InternalXApiError as exc:
                if self.db:
                    mark_guest_token_failed(self.db, token_record, str(exc))
                raise
        return extract_posts_from_x_json(payload, keyword)[:limit]

    async def _activate_guest(self, client: httpx.AsyncClient) -> str:
        response = await client.post("https://api.twitter.com/1.1/guest/activate.json")
        if response.status_code >= 400:
            raise InternalXApiError(f"guest token 获取失败：HTTP {response.status_code}")
        token = response.json().get("guest_token")
        if not token:
            raise InternalXApiError("guest token 响应中没有 guest_token")
        return str(token)

    async def _get_search_operation(self, client: httpx.AsyncClient) -> SearchOperation:
        if self._operation:
            return self._operation
        if self.db:
            cached = get_query_id(self.db, "SearchTimeline")
            if cached:
                self._operation = SearchOperation(query_id=cached.query_id)
                return self._operation
        response = await client.get("https://x.com/")
        script_urls = [match.group("src") for match in SCRIPT_RE.finditer(response.text)]
        prioritized = sorted(script_urls, key=lambda url: ("Search" not in url and "Routes" not in url, url))
        for script_url in prioritized[:24]:
            try:
                script_response = await client.get(urljoin("https://x.com/", script_url))
            except httpx.HTTPError:
                continue
            query_id = _extract_search_query_id(script_response.text)
            if query_id:
                self._operation = SearchOperation(query_id=query_id)
                if self.db:
                    store_query_id(self.db, "SearchTimeline", query_id, script_url)
                return self._operation
        raise InternalXApiError("未能从 X 前端脚本中发现 SearchTimeline queryId")

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
        response = await client.get(
            f"https://x.com/i/api/graphql/{operation.query_id}/SearchTimeline",
            params={
                "variables": json.dumps(variables, separators=(",", ":")),
                "features": json.dumps(features, separators=(",", ":")),
            },
            headers={
                "x-guest-token": guest_token,
                "x-twitter-active-user": "yes",
                "x-twitter-client-language": "en",
            },
        )
        if response.status_code >= 400:
            raise InternalXApiError(f"SearchTimeline 请求失败：HTTP {response.status_code} {response.text[:200]}")
        return response.json()


def _extract_search_query_id(script: str) -> str | None:
    for pattern in (SEARCH_OPERATION_RE, SEARCH_OPERATION_RE_REVERSED):
        match = pattern.search(script)
        if match:
            return match.group("query_id")
    return None


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
