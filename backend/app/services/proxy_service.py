from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.proxy import Proxy, ProxyStatus
from app.schemas.operations import ProxyCheckResult


def sync_env_proxies(db: Session) -> None:
    for index, proxy_url in enumerate(settings.proxy_url_list, start=1):
        name = f"env-{index}"
        proxy = db.scalar(select(Proxy).where(Proxy.name == name))
        if proxy is None:
            db.add(Proxy(name=name, proxy_url=proxy_url, status=ProxyStatus.ACTIVE))
        else:
            proxy.proxy_url = proxy_url
            if proxy.status == ProxyStatus.DISABLED:
                proxy.status = ProxyStatus.ACTIVE
    db.commit()


def choose_proxy(db: Session) -> Proxy | None:
    now = datetime.now(timezone.utc)
    sync_env_proxies(db)
    return db.scalar(
        select(Proxy)
        .where(Proxy.status == ProxyStatus.ACTIVE)
        .where((Proxy.cooldown_until.is_(None)) | (Proxy.cooldown_until <= now))
        .order_by(Proxy.failure_count.asc(), Proxy.last_checked_at.asc())
        .limit(1)
    )


def create_proxy(db: Session, name: str, proxy_url: str) -> Proxy:
    existing = db.scalar(select(Proxy).where(Proxy.name == name))
    if existing:
        raise HTTPException(status_code=409, detail="Proxy name already exists")
    proxy = Proxy(name=name, proxy_url=proxy_url, status=ProxyStatus.ACTIVE)
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy


def set_proxy_enabled(db: Session, proxy_id: int, enabled: bool) -> Proxy:
    proxy = db.get(Proxy, proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    proxy.status = ProxyStatus.ACTIVE if enabled else ProxyStatus.DISABLED
    if enabled:
        proxy.cooldown_until = None
    db.commit()
    db.refresh(proxy)
    return proxy


def mark_proxy_success(db: Session, proxy: Proxy | None) -> None:
    if not proxy:
        return
    proxy.success_count += 1
    proxy.last_error = None
    proxy.last_checked_at = datetime.now(timezone.utc)
    db.commit()


def mark_proxy_failure(db: Session, proxy: Proxy | None, message: str) -> None:
    if not proxy:
        return
    proxy.failure_count += 1
    proxy.last_error = message[:1000]
    proxy.last_checked_at = datetime.now(timezone.utc)
    if proxy.failure_count >= 3:
        proxy.status = ProxyStatus.COOLDOWN
        proxy.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.commit()


async def check_proxy(db: Session, proxy: Proxy) -> ProxyCheckResult:
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=8.0),
            follow_redirects=True,
            proxies=proxy.proxy_url,
            headers={
                "authorization": (
                    "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAA"
                    "kPxtR8GyrDMwUeUGQ8QFw8FyH0U%3D"
                    "CqHbxTnTn4j1nmrtuKqhoJkgS85FzJJGRwjiM5mT"
                ),
                "user-agent": "Mozilla/5.0 Chrome/130.0.0.0 Safari/537.36",
            },
        ) as client:
            response = await client.post("https://api.twitter.com/1.1/guest/activate.json")
        if response.status_code < 400 and response.json().get("guest_token"):
            proxy.status = ProxyStatus.ACTIVE
            proxy.success_count += 1
            proxy.last_error = None
            proxy.last_checked_at = datetime.now(timezone.utc)
            proxy.cooldown_until = None
            db.commit()
            return ProxyCheckResult(
                proxy_id=proxy.id,
                status=proxy.status,
                message="guest token 获取成功",
                guest_token_ok=True,
            )
        message = f"guest token 获取失败：HTTP {response.status_code}"
    except Exception as exc:
        message = str(exc)

    proxy.failure_count += 1
    proxy.last_error = message[:1000]
    proxy.last_checked_at = datetime.now(timezone.utc)
    proxy.status = ProxyStatus.COOLDOWN
    proxy.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.commit()
    return ProxyCheckResult(proxy_id=proxy.id, status=proxy.status, message=message, guest_token_ok=False)
