from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.crawler_session import CrawlerSession, CrawlerSessionStatus
from app.schemas.crawler_session import CrawlerSessionRead
from app.services.session_service import get_or_create_session, run_login_session, verify_session


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/primary", response_model=CrawlerSessionRead)
def get_primary_session(db: Session = Depends(get_db)) -> CrawlerSession:
    return get_or_create_session(db)


@router.post("/primary/verify", response_model=CrawlerSessionRead)
async def verify_primary_session(db: Session = Depends(get_db)) -> CrawlerSession:
    return await verify_session(db)


@router.post("/primary/login", response_model=CrawlerSessionRead, status_code=202)
def login_primary_session(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> CrawlerSession:
    session = get_or_create_session(db)
    if session.status == CrawlerSessionStatus.LOGIN_RUNNING:
        raise HTTPException(status_code=409, detail="登录窗口已经打开。")
    session.status = CrawlerSessionStatus.LOGIN_RUNNING
    session.last_error = None
    db.commit()
    db.refresh(session)
    background_tasks.add_task(run_login_session)
    return session
