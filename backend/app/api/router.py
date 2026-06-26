from __future__ import annotations

from fastapi import APIRouter

from app.api import crawl_jobs, posts

api_router = APIRouter(prefix="/api")
api_router.include_router(crawl_jobs.router)
api_router.include_router(posts.router)


@api_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
