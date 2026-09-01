from __future__ import annotations

import re
from html.parser import HTMLParser

from app.crawler.parser import parse_compact_count
from app.crawler.types import CrawledMedia, CrawledNote


AUTHOR_ID_RE = re.compile(r"/user/profile/([A-Za-z0-9]+)")


class _NoteCardParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.notes: list[CrawledNote] = []
        self._stack: list[tuple[str, set[str]]] = []
        self._card: dict | None = None
        self._card_section_depth: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        classes = set(attributes.get("class", "").split())
        self._stack.append((tag, classes))
        if tag == "section" and "note-item" in classes and self._card is None:
            self._card = {
                "note_id": attributes.get("data-note-id", ""),
                "note_url": "",
                "title": [],
                "author_id": None,
                "author_name": [],
                "author_avatar": None,
                "like_count": 0,
                "cover_url": None,
                "note_type": "normal",
            }
            self._card_section_depth = len(self._stack)
        if self._card is None:
            if tag in self.VOID_TAGS:
                self._stack.pop()
            return
        if tag == "a":
            href = attributes.get("href", "")
            if "/explore/" in href and (not self._card["note_url"] or "xsec_token=" in href):
                self._card["note_url"] = href
            if "author" in classes:
                match = AUTHOR_ID_RE.search(href)
                if match:
                    self._card["author_id"] = match.group(1)
        elif tag == "img":
            src = attributes.get("src", "")
            if "author-avatar" in classes:
                self._card["author_avatar"] = src or None
            elif src and self._inside_class("cover") and not self._card["cover_url"]:
                self._card["cover_url"] = src
        elif "play-icon" in classes:
            self._card["note_type"] = "video"
        if tag in self.VOID_TAGS:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._card is None or not data.strip():
            return
        if self._inside_class("title"):
            self._card["title"].append(data.strip())
        elif self._inside_class("name"):
            self._card["author_name"].append(data.strip())
        elif self._inside_class("count"):
            self._card["like_count"] = parse_compact_count(data)

    def handle_endtag(self, tag: str) -> None:
        if (
            self._card is not None
            and tag == "section"
            and self._card_section_depth == len(self._stack)
        ):
            note = self._build_note(self._card)
            if note:
                self.notes.append(note)
            self._card = None
            self._card_section_depth = None
        if self._stack:
            self._stack.pop()

    def _inside_class(self, class_name: str) -> bool:
        return any(class_name in classes for _, classes in self._stack)

    @staticmethod
    def _build_note(card: dict) -> CrawledNote | None:
        note_id = str(card.get("note_id") or "")
        title = " ".join(card.get("title") or []).strip()
        if not note_id or not title:
            return None
        relative_url = str(card.get("note_url") or f"/explore/{note_id}")
        note_url = relative_url if relative_url.startswith("http") else f"https://www.xiaohongshu.com{relative_url}"
        cover_url = card.get("cover_url")
        media_items = [CrawledMedia("image", cover_url, cover_url)] if cover_url else []
        return CrawledNote(
            platform_note_id=note_id,
            note_type=str(card.get("note_type") or "normal"),
            completeness="card",
            title=title,
            content="",
            note_url=note_url,
            author_id=card.get("author_id"),
            author_name=" ".join(card.get("author_name") or []).strip() or None,
            author_avatar=card.get("author_avatar"),
            published_at=None,
            like_count=int(card.get("like_count") or 0),
            media_items=media_items,
        )


def extract_notes_from_html(html: str) -> list[CrawledNote]:
    parser = _NoteCardParser()
    parser.feed(html)
    return list({note.platform_note_id: note for note in parser.notes}.values())
