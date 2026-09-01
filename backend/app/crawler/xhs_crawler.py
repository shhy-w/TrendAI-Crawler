from __future__ import annotations

import asyncio
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import httpx
from playwright.async_api import BrowserContext, Error as PlaywrightError, Page, Response, async_playwright

from app.core.config import settings
from app.crawler.html_extractor import extract_notes_from_html
from app.crawler.parser import extract_notes_from_payload, parse_compact_count, parse_note_id
from app.crawler.types import CrawledMedia, CrawledNote
from app.models.crawl_job import CrawlMode
from app.models.source import SourceType


PROFILE_LOCK = threading.Lock()


class XHSAuthRequiredError(RuntimeError):
    pass


class XHSCaptchaRequiredError(RuntimeError):
    pass


class XHSNoContentError(RuntimeError):
    pass


class XHSAccessRestrictedError(RuntimeError):
    pass


class XHSCrawler:
    def __init__(self, profile_dir: Path | None = None) -> None:
        self.profile_dir = profile_dir or settings.profile_path

    async def crawl_source(
        self,
        source_type: str,
        target: str,
        limit: int,
        mode: str = CrawlMode.AUTO,
    ) -> list[CrawledNote]:
        if source_type not in SourceType.VALUES:
            raise ValueError(f"不支持的信源类型：{source_type}")
        if mode not in CrawlMode.VALUES:
            raise ValueError(f"不支持的采集模式：{mode}")
        if mode == CrawlMode.PUBLIC:
            return await self._crawl_public(source_type, target, limit)
        if mode == CrawlMode.AUTHENTICATED:
            return await self._crawl_authenticated(source_type, target, limit)
        try:
            return await self._crawl_public(source_type, target, limit)
        except (XHSAuthRequiredError, XHSNoContentError) as public_error:
            try:
                return await self._crawl_authenticated(source_type, target, limit)
            except XHSAuthRequiredError as auth_error:
                raise XHSNoContentError(
                    f"匿名通道未获取到内容：{public_error} 登录通道不可用：{auth_error}"
                ) from auth_error

    async def _crawl_public(self, source_type: str, target: str, limit: int) -> list[CrawledNote]:
        page_url = self._source_url(source_type, target)
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.crawler_navigation_timeout_ms / 1000,
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "accept-language": "zh-CN,zh;q=0.9",
                "user-agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
                ),
            },
        ) as client:
            response = await client.get(page_url)
            response.raise_for_status()
            if "/website-login/error" in str(response.url) or "IP存在风险" in response.text:
                raise XHSAccessRestrictedError("小红书限制了当前 IP 或网络环境，请更换可靠网络后重试。")
            notes = extract_notes_from_html(response.text)
            if notes:
                return notes[:limit]

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=settings.crawler_headless)
            context = await browser.new_context(
                viewport={"width": 1440, "height": 1000},
                locale="zh-CN",
            )
            try:
                return await self._crawl_in_context(context, source_type, target, limit, CrawlMode.PUBLIC)
            finally:
                await context.close()
                await browser.close()

    async def _crawl_authenticated(self, source_type: str, target: str, limit: int) -> list[CrawledNote]:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(PROFILE_LOCK.acquire)
        try:
            async with async_playwright() as playwright:
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=settings.crawler_headless,
                    viewport={"width": 1440, "height": 1000},
                    locale="zh-CN",
                )
                try:
                    if not await self._has_session(context):
                        raise XHSAuthRequiredError("小红书登录态不存在或已过期，请先在登录会话页面完成扫码登录。")
                    return await self._crawl_in_context(context, source_type, target, limit, CrawlMode.AUTHENTICATED)
                finally:
                    await context.close()
        finally:
            PROFILE_LOCK.release()

    async def check_session(self) -> bool:
        if not self.profile_dir.exists():
            return False
        await asyncio.to_thread(PROFILE_LOCK.acquire)
        try:
            async with async_playwright() as playwright:
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=True,
                    viewport={"width": 1280, "height": 800},
                    locale="zh-CN",
                )
                try:
                    if not await self._has_session(context):
                        return False
                    page = context.pages[0] if context.pages else await context.new_page()
                    page.set_default_timeout(settings.crawler_navigation_timeout_ms)
                    await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
                    await page.wait_for_timeout(1200)
                    return not await self._has_blocking_login(page)
                finally:
                    await context.close()
        finally:
            PROFILE_LOCK.release()

    async def _crawl_in_context(
        self,
        context: BrowserContext,
        source_type: str,
        target: str,
        limit: int,
        mode: str,
    ) -> list[CrawledNote]:
        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_timeout(settings.crawler_navigation_timeout_ms)
        notes: dict[str, CrawledNote] = {}
        response_tasks: set[asyncio.Task] = set()

        def handle_response(response: Response) -> None:
            if "/api/" not in response.url or "xiaohongshu.com" not in response.url:
                return
            task = asyncio.create_task(self._extract_response(response, notes))
            response_tasks.add(task)
            task.add_done_callback(response_tasks.discard)

        page.on("response", handle_response)
        await page.goto(self._source_url(source_type, target), wait_until="domcontentloaded")
        for _ in range(settings.crawler_scroll_rounds):
            await page.wait_for_timeout(settings.crawler_scroll_pause_ms)
            if await self._has_access_restriction(page):
                await self._write_debug_artifacts(page, target, "access_restricted")
                raise XHSAccessRestrictedError("小红书限制了当前 IP 或网络环境，请更换可靠网络后重试。")
            if await self._has_captcha(page):
                await self._write_debug_artifacts(page, target, "captcha")
                raise XHSCaptchaRequiredError("小红书要求完成安全验证，任务已暂停，请在登录会话中人工处理。")
            if len(notes) >= limit:
                break
            await page.mouse.wheel(0, 1800)
        if response_tasks:
            await asyncio.gather(*list(response_tasks), return_exceptions=True)
        await page.wait_for_timeout(400)
        if await self._has_access_restriction(page):
            await self._write_debug_artifacts(page, target, "access_restricted")
            raise XHSAccessRestrictedError("小红书限制了当前 IP 或网络环境，请更换可靠网络后重试。")

        try:
            visible_notes = await self._parse_visible_notes(page)
        except PlaywrightError as exc:
            if "Execution context was destroyed" not in str(exc):
                raise
            await page.wait_for_load_state("domcontentloaded")
            if await self._has_access_restriction(page):
                await self._write_debug_artifacts(page, target, "access_restricted")
                raise XHSAccessRestrictedError("小红书限制了当前 IP 或网络环境，请更换可靠网络后重试。") from exc
            visible_notes = await self._parse_visible_notes(page)
        for note in visible_notes:
            notes.setdefault(note.platform_note_id, note)
        if source_type == SourceType.NOTE and not notes:
            note = await self._parse_note_detail(page)
            if note:
                notes[note.platform_note_id] = note
        if not notes:
            await self._write_debug_artifacts(page, target, "empty")
            if mode == CrawlMode.AUTHENTICATED and await self._has_blocking_login(page):
                raise XHSAuthRequiredError("小红书登录态已失效，请重新扫码登录。")
            channel = "匿名" if mode == CrawlMode.PUBLIC else "登录"
            raise XHSNoContentError(f"{channel}通道未采集到笔记内容，已保存调试文件：{settings.debug_path}")
        return list(notes.values())[:limit]

    async def _extract_response(self, response: Response, notes: dict[str, CrawledNote]) -> None:
        try:
            payload = await response.json()
        except Exception:
            return
        for note in extract_notes_from_payload(payload):
            existing = notes.get(note.platform_note_id)
            if existing is None or len(note.content) > len(existing.content):
                notes[note.platform_note_id] = note

    async def _parse_visible_notes(self, page: Page) -> list[CrawledNote]:
        result: list[CrawledNote] = []
        for card in await page.locator("section.note-item, .note-item").all():
            link = card.locator('a[href*="/explore/"]').first
            href = await link.get_attribute("href") if await link.count() else None
            note_id = parse_note_id(href or "")
            if not note_id or not href:
                continue
            full_url = href if href.startswith("http") else f"https://www.xiaohongshu.com{href}"
            title_locator = card.locator(".title, .title span").first
            author_locator = card.locator(".author .name, .name").first
            count_locator = card.locator(".like-wrapper .count, .count").last
            image = card.locator("img").first
            image_url = await image.get_attribute("src") if await image.count() else None
            result.append(
                CrawledNote(
                    platform_note_id=note_id,
                    note_type="normal",
                    completeness="card",
                    title=(await title_locator.inner_text()).strip() if await title_locator.count() else "",
                    content="",
                    note_url=full_url,
                    author_id=None,
                    author_name=(await author_locator.inner_text()).strip() if await author_locator.count() else None,
                    author_avatar=None,
                    published_at=None,
                    like_count=parse_compact_count(await count_locator.inner_text()) if await count_locator.count() else 0,
                    media_items=[CrawledMedia("image", image_url, image_url)] if image_url else [],
                )
            )
        return result

    async def _parse_note_detail(self, page: Page) -> CrawledNote | None:
        note_id = parse_note_id(page.url)
        if not note_id:
            return None
        title_locator = page.locator("#detail-title, .note-content .title, .title").first
        content_locator = page.locator("#detail-desc, .note-content .desc, .desc").first
        author_locator = page.locator(".author-wrapper .username, .author-container .name").first
        title = (await title_locator.inner_text()).strip() if await title_locator.count() else ""
        content = (await content_locator.inner_text()).strip() if await content_locator.count() else ""
        if not title and not content:
            return None
        images: list[CrawledMedia] = []
        for index, image in enumerate(await page.locator(".note-content img, .swiper-slide img").all()):
            url = await image.get_attribute("src")
            if url:
                images.append(CrawledMedia("image", url, url, sort_order=index))
        return CrawledNote(
            platform_note_id=note_id,
            note_type="normal",
            completeness="complete" if content and images else "partial",
            title=title,
            content=content,
            note_url=page.url,
            author_id=None,
            author_name=(await author_locator.inner_text()).strip() if await author_locator.count() else None,
            author_avatar=None,
            published_at=None,
            media_items=images,
        )

    async def _has_session(self, context: BrowserContext) -> bool:
        cookies = await context.cookies("https://www.xiaohongshu.com")
        return any(cookie.get("name") == "web_session" and cookie.get("value") for cookie in cookies)

    async def _has_blocking_login(self, page: Page) -> bool:
        login_dialog = page.locator(".login-container, .login-modal, .login-wrapper")
        return bool(await login_dialog.count() and await login_dialog.first.is_visible())

    async def _has_captcha(self, page: Page) -> bool:
        for text in ("请完成验证", "安全验证", "拖动滑块", "异常访问"):
            if await page.get_by_text(text, exact=False).count():
                return True
        return False

    async def _has_access_restriction(self, page: Page) -> bool:
        for _ in range(2):
            if "/website-login/error" in page.url:
                return True
            try:
                return bool(await page.get_by_text("IP存在风险", exact=False).count())
            except PlaywrightError as exc:
                if "Execution context was destroyed" not in str(exc):
                    raise
                await page.wait_for_load_state("domcontentloaded")
        return "/website-login/error" in page.url

    def _source_url(self, source_type: str, target: str) -> str:
        if source_type == SourceType.EXPLORE:
            return f"https://www.xiaohongshu.com/explore?channel_id={quote_plus(target)}"
        if source_type == SourceType.KEYWORD:
            return f"https://www.xiaohongshu.com/search_result?keyword={quote_plus(target)}&source=web_search_result_notes"
        if not re.match(r"^https://(?:www\.)?xiaohongshu\.com/", target):
            raise ValueError("博主和笔记信源必须使用小红书网页链接。")
        return target

    async def _write_debug_artifacts(self, page: Page, target: str, reason: str) -> None:
        settings.debug_path.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_target = re.sub(r"[^A-Za-z0-9_-]+", "_", target).strip("_")[:64] or "source"
        base = settings.debug_path / f"{stamp}_{reason}_{safe_target}"
        base.with_suffix(".html").write_text(await page.content(), encoding="utf-8")
        base.with_suffix(".json").write_text(json.dumps({"url": page.url, "target": target, "reason": reason}, ensure_ascii=False, indent=2), encoding="utf-8")
        await page.screenshot(path=str(base.with_suffix(".png")), full_page=True)


async def open_xhs_login(profile_dir: Path | None = None) -> None:
    profile = profile_dir or settings.profile_path
    profile.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(PROFILE_LOCK.acquire)
    try:
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile),
                headless=False,
                viewport={"width": 1280, "height": 900},
                locale="zh-CN",
            )
            closed = asyncio.get_running_loop().create_future()
            context.on("close", lambda: closed.done() or closed.set_result(None))
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded")
            await closed
    finally:
        PROFILE_LOCK.release()
