from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.guest_token import GuestToken, GuestTokenStatus
from app.models.query_id_cache import QueryIdCache
from app.models.web_bearer_token import WebBearerToken, WebBearerTokenStatus


def get_active_guest_token(db: Session, proxy_id: int | None) -> GuestToken | None:
    now = datetime.now(timezone.utc)
    return db.scalar(
        select(GuestToken)
        .where(GuestToken.proxy_id == proxy_id)
        .where(GuestToken.status == GuestTokenStatus.ACTIVE)
        .where(GuestToken.expires_at > now)
        .order_by(GuestToken.updated_at.desc())
        .limit(1)
    )


def store_guest_token(db: Session, proxy_id: int | None, token: str) -> GuestToken:
    guest_token = GuestToken(
        proxy_id=proxy_id,
        guest_token=token,
        status=GuestTokenStatus.ACTIVE,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        last_success_at=datetime.now(timezone.utc),
    )
    db.add(guest_token)
    db.commit()
    db.refresh(guest_token)
    return guest_token


def mark_guest_token_failed(db: Session, token: GuestToken | None, message: str) -> None:
    if not token:
        return
    token.status = GuestTokenStatus.FAILED
    token.failure_count += 1
    token.last_error = message[:1000]
    db.commit()


def get_active_web_bearer_token(db: Session) -> WebBearerToken | None:
    now = datetime.now(timezone.utc)
    return db.scalar(
        select(WebBearerToken)
        .where(WebBearerToken.status == WebBearerTokenStatus.ACTIVE)
        .where(WebBearerToken.expires_at > now)
        .order_by(WebBearerToken.updated_at.desc())
        .limit(1)
    )


def store_web_bearer_token(db: Session, token: str, source_url: str | None) -> WebBearerToken:
    cached = get_active_web_bearer_token(db)
    if cached is None:
        cached = WebBearerToken(token=token, status=WebBearerTokenStatus.ACTIVE, expires_at=datetime.now(timezone.utc))
        db.add(cached)
    cached.token = token
    cached.source_url = source_url
    cached.status = WebBearerTokenStatus.ACTIVE
    cached.last_error = None
    cached.expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
    cached.last_success_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cached)
    return cached


def mark_web_bearer_token_failed(db: Session, token: WebBearerToken | None, message: str) -> None:
    if not token:
        return
    token.status = WebBearerTokenStatus.FAILED
    token.failure_count += 1
    token.last_error = message[:1000]
    db.commit()


def get_query_id(db: Session, operation_name: str) -> QueryIdCache | None:
    now = datetime.now(timezone.utc)
    return db.scalar(
        select(QueryIdCache)
        .where(QueryIdCache.operation_name == operation_name)
        .where(QueryIdCache.expires_at > now)
        .limit(1)
    )


def store_query_id(db: Session, operation_name: str, query_id: str, source_url: str | None) -> QueryIdCache:
    cached = db.scalar(select(QueryIdCache).where(QueryIdCache.operation_name == operation_name))
    if cached is None:
        cached = QueryIdCache(operation_name=operation_name, query_id=query_id, expires_at=datetime.now(timezone.utc))
        db.add(cached)
    cached.query_id = query_id
    cached.source_url = source_url
    cached.expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
    db.commit()
    db.refresh(cached)
    return cached
