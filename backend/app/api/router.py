from __future__ import annotations

from fastapi import APIRouter

from app.api import crawl_jobs, notes, sessions, sources

api_router = APIRouter(prefix="/api")
api_router.include_router(crawl_jobs.router)
api_router.include_router(notes.router)
api_router.include_router(sessions.router)
api_router.include_router(sources.router)


@api_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "platform": "xiaohongshu"}
