from datetime import datetime, timedelta, timezone

import pytest

from app.crawler.errors import CrawlFailureType
from app.models.crawler_session import CrawlerSessionStatus
from app.services.account_protection_service import (
    AccountProtectionError,
    record_authenticated_failure,
    record_authenticated_success,
    reserve_authenticated_access,
    update_account_protection,
)
from app.services.session_service import get_or_create_session


def test_authenticated_budget_and_cooldown_are_enforced(db_session) -> None:
    session = get_or_create_session(db_session)
    session.daily_request_limit = 10
    session.cooldown_seconds = 30
    db_session.commit()
    now = datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc)

    assert reserve_authenticated_access(db_session, cost=7, now=now) == 0
    assert reserve_authenticated_access(db_session, cost=1, now=now + timedelta(seconds=5)) == 25
    assert session.daily_request_count == 8

    with pytest.raises(AccountProtectionError, match="预算剩余"):
        reserve_authenticated_access(db_session, cost=3, now=now + timedelta(minutes=1))


def test_risk_failures_trigger_lockout_and_success_resets_counter(db_session) -> None:
    session = get_or_create_session(db_session)
    session.failure_threshold = 2
    session.lockout_minutes = 60
    db_session.commit()
    now = datetime(2026, 9, 1, 1, 0, tzinfo=timezone.utc)

    record_authenticated_failure(db_session, CrawlFailureType.CAPTCHA_REQUIRED, "安全验证", now=now)
    assert session.consecutive_failures == 1
    record_authenticated_success(db_session)
    assert session.consecutive_failures == 0

    record_authenticated_failure(db_session, CrawlFailureType.ACCESS_RESTRICTED, "风险网络", now=now)
    record_authenticated_failure(db_session, CrawlFailureType.RATE_LIMITED, "限频", now=now)
    assert session.status == CrawlerSessionStatus.PROTECTION_BLOCKED
    assert session.blocked_until == now + timedelta(hours=1)

    with pytest.raises(AccountProtectionError, match="恢复时间"):
        reserve_authenticated_access(db_session, cost=1, now=now + timedelta(minutes=10))


def test_disabling_protection_clears_lockout(db_session) -> None:
    session = get_or_create_session(db_session)
    session.status = CrawlerSessionStatus.PROTECTION_BLOCKED
    session.blocked_until = datetime.now(timezone.utc) + timedelta(hours=1)
    session.consecutive_failures = 2
    db_session.commit()

    updated = update_account_protection(
        db_session,
        protection_enabled=False,
        daily_request_limit=60,
        cooldown_seconds=30,
        failure_threshold=2,
        lockout_minutes=360,
    )

    assert updated.blocked_until is None
    assert updated.consecutive_failures == 0
    assert updated.status == CrawlerSessionStatus.ACTIVE
