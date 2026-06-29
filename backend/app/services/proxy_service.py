from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crawler.internal_api import InternalXApiCrawler, WEB_BEARER_TOKEN
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
                "user-agent": "Mozilla/5.0 Chrome/130.0.0.0 Safari/537.36",
                "origin": "https://x.com",
                "referer": "https://x.com/",
            },
        ) as client:
            bearer = await InternalXApiCrawler(proxy_url=proxy.proxy_url, db=db, proxy_id=proxy.id)._ensure_web_bearer(client)
            client.headers["authorization"] = f"Bearer {bearer.token if bearer else WEB_BEARER_TOKEN}"
            response = await client.post("https://api.twitter.com/1.1/guest/activate.json")
            if response.status_code in {401, 403}:
                reachability_response = await client.get("https://api.twitter.com/robots.txt")
                if reachability_response.status_code < 500:
                    proxy.status = ProxyStatus.ACTIVE
                    proxy.last_error = f"guest token 获取失败：HTTP {response.status_code}"
                    proxy.last_checked_at = datetime.now(timezone.utc)
                    proxy.cooldown_until = None
                    db.commit()
                    return ProxyCheckResult(
                        proxy_id=proxy.id,
                        status=proxy.status,
                        message=(
                            f"代理网络可达，但 guest token 获取失败：HTTP {response.status_code}。"
                            "需要更新 X Web Bearer 或切换采集策略。"
                        ),
                        guest_token_ok=False,
                    )
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
        message = str(exc) or exc.__class__.__name__

    proxy.failure_count += 1
    proxy.last_error = message[:1000]
    proxy.last_checked_at = datetime.now(timezone.utc)
    proxy.status = ProxyStatus.COOLDOWN
    proxy.cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.commit()
    return ProxyCheckResult(proxy_id=proxy.id, status=proxy.status, message=message, guest_token_ok=False)
