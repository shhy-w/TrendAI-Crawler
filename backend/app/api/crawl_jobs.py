from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.models.crawl_job import CrawlJob
from app.schemas.crawl_job import CrawlJobCreate, CrawlJobRead
from app.services.crawl_service import create_crawl_job, run_crawl_job


router = APIRouter(prefix="/crawl-jobs", tags=["crawl-jobs"])


@router.post("", response_model=CrawlJobRead, status_code=201)
def create_job(payload: CrawlJobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> CrawlJob:
    try:
        job = create_crawl_job(db, payload.source_ids, payload.max_notes_per_source, payload.crawl_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(run_crawl_job, job.id)
    return job


@router.get("", response_model=list[CrawlJobRead])
def list_jobs(limit: int = 20, db: Session = Depends(get_db)) -> list[CrawlJob]:
    statement = select(CrawlJob).options(selectinload(CrawlJob.items)).order_by(CrawlJob.created_at.desc()).limit(min(limit, 100))
    return list(db.scalars(statement))
