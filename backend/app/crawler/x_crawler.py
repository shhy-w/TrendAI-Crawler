from __future__ import annotations

import json
import re
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from playwright.async_api import Browser, BrowserContext, Page, Response, async_playwright

from app.core.config import settings
from app.crawler.internal_api import InternalXApiCrawler, InternalXApiError
from app.crawler.json_extractor import extract_posts_from_x_json
from app.crawler.parser import build_crawled_post
from app.crawler.types import CrawledPost


class XLoginRequiredError(RuntimeError):
    pass


class XNoContentError(RuntimeError):
    pass


class BasePlaywrightXCrawler:
    def _search_url(self, keyword: str) -> str:
        query_text = keyword
        if settings.crawler_min_faves > 0:
            query_text = f"{keyword} min_faves:{settings.crawler_min_faves}"
        query = quote_plus(query_text)
        return f"https://x.com/search?q={query}&src=typed_query&f=top"

    async def _prepare_page(self, context: BrowserContext, keyword: str) -> Page:
        page = await context.new_page()
        page.set_default_timeout(settings.crawler_navigation_timeout_ms)
        await page.goto(self._search_url(keyword), wait_until="domcontentloaded")
        return page

    async def _collect_posts(self, page: Page, keyword: str, limit: int) -> list[CrawledPost]:
        posts_by_id: dict[str, CrawledPost] = {}
        for _ in range(settings.crawler_scroll_rounds):
            for post in await self._parse_visible_articles(page, keyword):
                posts_by_id[post.x_post_id] = post
                if len(posts_by_id) >= limit:
                    return list(posts_by_id.values())[:limit]
            await page.mouse.wheel(0, 2400)
            await page.wait_for_timeout(settings.crawler_scroll_pause_ms)
        return list(posts_by_id.values())[:limit]

    async def _parse_visible_articles(self, page: Page, keyword: str) -> list[CrawledPost]:
        articles = await page.locator("article").all()
        parsed: list[CrawledPost] = []
        for article in articles:
            status_links = await article.locator('a[href*="/status/"]').all()
            post_url = None
            for link in status_links:
                href = await link.get_attribute("href")
                if href and "/status/" in href:
                    post_url = href if href.startswith("http") else f"https://x.com{href}"
                    break
            if not post_url:
                continue

            text_parts = await article.locator('[data-testid="tweetText"]').all_inner_texts()
            text = "\n".join(part.strip() for part in text_parts if part.strip())
            author_blob = await article.inner_text()
            author_name = author_blob.split("\n", 1)[0].strip() if author_blob else None
            time_value = None
            if await article.locator("time").count():
                time_value = await article.locator("time").first.get_attribute("datetime")

            image_urls = await self._image_urls(article)
            metrics = await self._metrics(article)
            post = build_crawled_post(
                keyword=keyword,
                post_url=post_url,
                text=text,
                author_name=author_name,
                author_blob=author_blob,
                published_at=time_value,
                media_urls=image_urls,
                metrics=metrics,
            )
            if post:
                parsed.append(post)
        return parsed

    async def _image_urls(self, article) -> list[str]:
        urls: list[str] = []
        for image in await article.locator('img[src*="twimg.com/media"], img[src*="pbs.twimg.com/media"]').all():
            src = await image.get_attribute("src")
            if src:
                urls.append(src)
        for video in await article.locator("video").all():
            poster = await video.get_attribute("poster")
            src = await video.get_attribute("src")
            if src:
                urls.append(src)
            elif poster:
                urls.append(poster)
        return urls

    async def _metrics(self, article) -> dict[str, str | None]:
        testids = {
            "reply": "reply",
            "repost": "retweet",
            "like": "like",
        }
        metrics: dict[str, str | None] = {}
        for key, testid in testids.items():
            locator = article.locator(f'[data-testid="{testid}"]')
            metrics[key] = await locator.first.get_attribute("aria-label") if await locator.count() else None
        view_locator = article.locator('a[href*="/analytics"]')
        metrics["view"] = await view_locator.first.get_attribute("aria-label") if await view_locator.count() else None
        return metrics

    async def _has_login_prompt(self, page: Page) -> bool:
        login_link = page.get_by_role("link", name="Log in")
        login_button = page.get_by_role("button", name="Log in")
        return bool(await login_link.count() or await login_button.count())


class PublicXCrawler(BasePlaywrightXCrawler):
    def __init__(self, proxy_url: str | None = None, db=None, proxy_id: int | None = None) -> None:
        self.proxy_url = proxy_url
        self.internal_api = InternalXApiCrawler(proxy_url=proxy_url, db=db, proxy_id=proxy_id)

    async def crawl_keyword(self, keyword: str, limit: int) -> list[CrawledPost]:
        internal_error: Exception | None = None
        try:
            posts = await self.internal_api.crawl_keyword(keyword, limit)
            if posts:
                return posts
        except InternalXApiError as exc:
            internal_error = exc

        async with async_playwright() as playwright:
            launch_kwargs = {"headless": settings.crawler_headless}
            if self.proxy_url:
                launch_kwargs["proxy"] = {"server": self.proxy_url}
            browser: Browser = await playwright.chromium.launch(**launch_kwargs)
            try:
                posts_by_id: dict[str, CrawledPost] = {}
                context = await browser.new_context(
                    viewport={"width": 1440, "height": 1100},
                    locale="en-US",
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/130.0.0.0 Safari/537.36"
                    ),
                )
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                page = await context.new_page()
                page.set_default_timeout(settings.crawler_navigation_timeout_ms)
                page.on("response", lambda response: self._capture_json_response(response, keyword, posts_by_id))
                await page.goto(self._search_url(keyword), wait_until="domcontentloaded")
                await self._wait_for_search_surface(page)
                posts = list(posts_by_id.values())[:limit]
                if not posts:
                    posts = await self._collect_posts(page, keyword, limit)
                if posts:
                    return posts
                await self._write_debug_artifacts(page, keyword)
                if await self._has_login_prompt(page):
                    raise XLoginRequiredError(
                        f"公开通道被 X 登录墙阻断。内部接口错误：{internal_error}。调试文件：{settings.debug_path}"
                    )
                raise XNoContentError(
                    f"公开通道未采集到内容。内部接口错误：{internal_error}。调试文件：{settings.debug_path}"
                )
            finally:
                if "context" in locals():
                    await context.close()
                await browser.close()

    async def _wait_for_search_surface(self, page: Page) -> None:
        for _ in range(settings.crawler_scroll_rounds):
            await page.wait_for_timeout(settings.crawler_scroll_pause_ms)
            if await page.locator("article").count():
                return
            await page.mouse.wheel(0, 2400)

    def _capture_json_response(self, response: Response, keyword: str, posts_by_id: dict[str, CrawledPost]) -> None:
        if not _looks_like_x_data_response(response.url):
            return

        async def parse_response() -> None:
            try:
                payload = await response.json()
            except Exception:
                return
            for post in extract_posts_from_x_json(payload, keyword):
                posts_by_id[post.x_post_id] = post

        asyncio.create_task(parse_response())

    async def _write_debug_artifacts(self, page: Page, keyword: str) -> None:
        settings.debug_path.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_keyword = re.sub(r"[^A-Za-z0-9_-]+", "_", keyword).strip("_") or "keyword"
        base = settings.debug_path / f"{stamp}_{safe_keyword}"
        html = await page.content()
        (base.with_suffix(".html")).write_text(html, encoding="utf-8")
        (base.with_suffix(".json")).write_text(
            json.dumps(
                {
                    "url": page.url,
                    "keyword": keyword,
                    "has_login_prompt": await self._has_login_prompt(page),
                    "article_count": await page.locator("article").count(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        await page.screenshot(path=str(base.with_suffix(".png")), full_page=True)


class AuthenticatedXCrawler(BasePlaywrightXCrawler):
    def __init__(self, profile_dir: Path | None = None, proxy_url: str | None = None) -> None:
        self.profile_dir = profile_dir or settings.profile_path
        self.proxy_url = proxy_url

    async def crawl_keyword(self, keyword: str, limit: int) -> list[CrawledPost]:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        async with async_playwright() as playwright:
            launch_kwargs = {
                "user_data_dir": str(self.profile_dir),
                "headless": settings.crawler_headless,
                "viewport": {"width": 1440, "height": 1100},
            }
            if self.proxy_url:
                launch_kwargs["proxy"] = {"server": self.proxy_url}
            context = await playwright.chromium.launch_persistent_context(
                **launch_kwargs,
            )
            try:
                page = await self._prepare_page(context, keyword)
                await self._ensure_accessible(page)
                return await self._collect_posts(page, keyword, limit)
            finally:
                await context.close()

    async def _ensure_accessible(self, page: Page) -> None:
        has_login_prompt = await self._has_login_prompt(page)
        if settings.crawler_require_login and has_login_prompt:
            raise XLoginRequiredError(
                "X 登录态不存在或已过期，请先运行 backend/scripts/open_x_login.py 手动登录。"
            )
        if has_login_prompt and not await page.locator("article").count():
            raise XLoginRequiredError(
                "当前公开页面未返回可采集内容。可先运行 backend/scripts/open_x_login.py 登录，"
                "或稍后重试公开采集。"
            )


class DualChannelXCrawler:
    def __init__(self, proxy_url: str | None = None, db=None, proxy_id: int | None = None) -> None:
        self.public_crawler = PublicXCrawler(proxy_url=proxy_url, db=db, proxy_id=proxy_id)
        self.authenticated_crawler = AuthenticatedXCrawler(proxy_url=proxy_url)

    async def crawl_keyword(self, keyword: str, limit: int) -> list[CrawledPost]:
        channel = settings.crawler_channel.lower()
        if channel == "public":
            return await self.public_crawler.crawl_keyword(keyword, limit)
        if channel == "authenticated":
            return await self.authenticated_crawler.crawl_keyword(keyword, limit)
        public_error: Exception | None = None
        try:
            posts = await self.public_crawler.crawl_keyword(keyword, limit)
            if posts:
                return posts
        except (XLoginRequiredError, XNoContentError) as exc:
            public_error = exc

        if not settings.crawler_fallback_to_auth:
            raise XNoContentError(
                f"{public_error} 已禁用登录态 fallback，不会打开登录窗口。"
            )

        try:
            return await self.authenticated_crawler.crawl_keyword(keyword, limit)
        except XLoginRequiredError as auth_error:
            if public_error:
                raise XLoginRequiredError(f"{public_error} 登录态通道也不可用：{auth_error}") from auth_error
            raise


XCrawler = DualChannelXCrawler


def _looks_like_x_data_response(url: str) -> bool:
    lowered = url.lower()
    return (
        ("x.com/i/api/graphql" in lowered or "twitter.com/i/api/graphql" in lowered)
        and any(marker in lowered for marker in ("searchtimeline", "searchtimeline", "tweet", "timeline"))
    )


async def open_login_browser() -> None:
    settings.profile_path.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        context: BrowserContext = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(settings.profile_path),
            headless=False,
            viewport={"width": 1440, "height": 1100},
        )
        page = await context.new_page()
        await page.goto("https://x.com/home", wait_until="domcontentloaded")
        print("请在打开的浏览器中完成 X 登录。登录成功后关闭浏览器窗口或按 Ctrl+C 结束脚本。")
        try:
            await page.wait_for_timeout(24 * 60 * 60 * 1000)
        finally:
            await context.close()
