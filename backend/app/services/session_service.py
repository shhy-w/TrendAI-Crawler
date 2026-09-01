from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawler.xhs_crawler import XHSCrawler, open_xhs_login
from app.db.session import SessionLocal
from app.models.crawler_session import CrawlerSession, CrawlerSessionStatus


PRIMARY_SESSION_NAME = "主会话"


def get_or_create_session(db: Session) -> CrawlerSession:
    session = db.scalar(select(CrawlerSession).where(CrawlerSession.name == PRIMARY_SESSION_NAME))
    if session is None:
        session = CrawlerSession(name=PRIMARY_SESSION_NAME, status=CrawlerSessionStatus.UNKNOWN)
        db.add(session)
        db.commit()
        db.refresh(session)
    return session


async def verify_session(db: Session) -> CrawlerSession:
    session = get_or_create_session(db)
    session.status = CrawlerSessionStatus.VERIFYING
    session.last_error = None
    db.commit()
    try:
        active = await XHSCrawler().check_session()
        session.status = CrawlerSessionStatus.ACTIVE if active else CrawlerSessionStatus.AUTH_REQUIRED
    except Exception as exc:
        session.status = CrawlerSessionStatus.ERROR
        session.last_error = str(exc)[:1024]
    session.last_verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return session


def run_login_session() -> None:
    db = SessionLocal()
    try:
        session = get_or_create_session(db)
        session.status = CrawlerSessionStatus.LOGIN_RUNNING
        session.last_error = None
        db.commit()
        try:
            asyncio.run(open_xhs_login())
            active = asyncio.run(XHSCrawler().check_session())
            session.status = CrawlerSessionStatus.ACTIVE if active else CrawlerSessionStatus.AUTH_REQUIRED
        except Exception as exc:
            session.status = CrawlerSessionStatus.ERROR
            session.last_error = str(exc)[:1024]
        session.last_verified_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()
