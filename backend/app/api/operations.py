from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.crawl_failure import CrawlFailure
from app.models.guest_token import GuestToken
from app.models.proxy import Proxy
from app.models.query_id_cache import QueryIdCache
from app.schemas.operations import CrawlFailureRead, GuestTokenRead, ProxyCheckResult, ProxyCreate, ProxyRead, QueryIdCacheRead
from app.services.proxy_service import check_proxy, create_proxy, set_proxy_enabled, sync_env_proxies

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/proxies", response_model=list[ProxyRead])
def list_proxies(db: Session = Depends(get_db)) -> list[Proxy]:
    sync_env_proxies(db)
    return list(db.scalars(select(Proxy).order_by(Proxy.id.asc())))


@router.post("/proxies", response_model=ProxyRead, status_code=201)
def add_proxy(payload: ProxyCreate, db: Session = Depends(get_db)) -> Proxy:
    return create_proxy(db, payload.name, payload.proxy_url)


@router.post("/proxies/{proxy_id}/check", response_model=ProxyCheckResult)
async def check_one_proxy(proxy_id: int, db: Session = Depends(get_db)) -> ProxyCheckResult:
    proxy = db.get(Proxy, proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return await check_proxy(db, proxy)


@router.post("/proxies/check", response_model=list[ProxyCheckResult])
async def check_all_proxies(db: Session = Depends(get_db)) -> list[ProxyCheckResult]:
    sync_env_proxies(db)
    proxies = list(db.scalars(select(Proxy).order_by(Proxy.id.asc())))
    return [await check_proxy(db, proxy) for proxy in proxies]


@router.post("/proxies/{proxy_id}/enable", response_model=ProxyRead)
def enable_proxy(proxy_id: int, db: Session = Depends(get_db)) -> Proxy:
    return set_proxy_enabled(db, proxy_id, enabled=True)


@router.post("/proxies/{proxy_id}/disable", response_model=ProxyRead)
def disable_proxy(proxy_id: int, db: Session = Depends(get_db)) -> Proxy:
    return set_proxy_enabled(db, proxy_id, enabled=False)


@router.get("/failures", response_model=list[CrawlFailureRead])
def list_failures(limit: int = 20, db: Session = Depends(get_db)) -> list[CrawlFailure]:
    statement = select(CrawlFailure).order_by(CrawlFailure.created_at.desc()).limit(min(limit, 100))
    return list(db.scalars(statement))


@router.get("/guest-tokens", response_model=list[GuestTokenRead])
def list_guest_tokens(db: Session = Depends(get_db)) -> list[GuestToken]:
    return list(db.scalars(select(GuestToken).order_by(GuestToken.updated_at.desc()).limit(100)))


@router.get("/query-ids", response_model=list[QueryIdCacheRead])
def list_query_ids(db: Session = Depends(get_db)) -> list[QueryIdCache]:
    return list(db.scalars(select(QueryIdCache).order_by(QueryIdCache.updated_at.desc()).limit(100)))
