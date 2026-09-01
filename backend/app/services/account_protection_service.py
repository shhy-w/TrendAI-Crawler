from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawler.errors import CrawlFailureType
from app.models.crawler_session import CrawlerSession, CrawlerSessionStatus
from app.services.session_service import PRIMARY_SESSION_NAME, get_or_create_session


RISK_FAILURE_TYPES = {
    CrawlFailureType.ACCESS_RESTRICTED,
    CrawlFailureType.CAPTCHA_REQUIRED,
    CrawlFailureType.RATE_LIMITED,
}


class AccountProtectionError(RuntimeError):
    pass


def reserve_authenticated_access(
    db: Session,
    cost: int,
    now: datetime | None = None,
) -> float:
    get_or_create_session(db)
    session = _locked_session(db)
    current = now or datetime.now(timezone.utc)
    today = current.astimezone(ZoneInfo("Asia/Shanghai")).date()
    if session.daily_request_date != today:
        session.daily_request_date = today
        session.daily_request_count = 0

    if session.blocked_until:
        blocked_until = _aware_utc(session.blocked_until)
        if blocked_until > current:
            raise AccountProtectionError(
                f"账号保护已暂停登录采集，恢复时间：{blocked_until.astimezone(ZoneInfo('Asia/Shanghai')).strftime('%m-%d %H:%M')}。"
            )
        session.blocked_until = None
        session.consecutive_failures = 0
        if session.status == CrawlerSessionStatus.PROTECTION_BLOCKED:
            session.status = CrawlerSessionStatus.ACTIVE

    if not session.protection_enabled:
        db.commit()
        return 0
    if session.daily_request_count + cost > session.daily_request_limit:
        raise AccountProtectionError(
            f"账号保护阻止了本次登录采集：今日预算剩余 {max(0, session.daily_request_limit - session.daily_request_count)}，"
            f"本次预计需要 {cost}。"
        )

    wait_seconds = 0.0
    if session.last_request_at:
        elapsed = (current - _aware_utc(session.last_request_at)).total_seconds()
        wait_seconds = max(0.0, session.cooldown_seconds - elapsed)
    session.daily_request_count += cost
    session.last_request_at = current + timedelta(seconds=wait_seconds)
    db.commit()
    return wait_seconds


def record_authenticated_success(db: Session) -> None:
    get_or_create_session(db)
    session = _locked_session(db)
    session.consecutive_failures = 0
    db.commit()


def record_authenticated_failure(
    db: Session,
    failure_type: str,
    message: str,
    now: datetime | None = None,
) -> None:
    if failure_type not in RISK_FAILURE_TYPES:
        return
    get_or_create_session(db)
    session = _locked_session(db)
    if not session.protection_enabled:
        db.commit()
        return
    session.consecutive_failures += 1
    if session.consecutive_failures >= session.failure_threshold:
        current = now or datetime.now(timezone.utc)
        session.blocked_until = current + timedelta(minutes=session.lockout_minutes)
        session.status = CrawlerSessionStatus.PROTECTION_BLOCKED
        session.last_error = f"账号保护已触发：{message}"[:1024]
    db.commit()


def update_account_protection(
    db: Session,
    *,
    protection_enabled: bool,
    daily_request_limit: int,
    cooldown_seconds: int,
    failure_threshold: int,
    lockout_minutes: int,
) -> CrawlerSession:
    session = get_or_create_session(db)
    session.protection_enabled = protection_enabled
    session.daily_request_limit = daily_request_limit
    session.cooldown_seconds = cooldown_seconds
    session.failure_threshold = failure_threshold
    session.lockout_minutes = lockout_minutes
    if not protection_enabled:
        session.blocked_until = None
        session.consecutive_failures = 0
        if session.status == CrawlerSessionStatus.PROTECTION_BLOCKED:
            session.status = CrawlerSessionStatus.ACTIVE
    db.commit()
    db.refresh(session)
    return session


def _locked_session(db: Session) -> CrawlerSession:
    return db.scalar(
        select(CrawlerSession)
        .where(CrawlerSession.name == PRIMARY_SESSION_NAME)
        .with_for_update()
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
