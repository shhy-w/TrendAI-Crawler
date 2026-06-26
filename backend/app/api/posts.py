from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.models.media import Media
from app.models.post import Post
from app.schemas.post import PostListResponse, PostRead

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=PostListResponse)
def list_posts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = None,
    author: Optional[str] = None,
    has_media: Optional[bool] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    sort: str = Query(default="hot", pattern="^(hot|published_at|crawled_at)$"),
    db: Session = Depends(get_db),
) -> PostListResponse:
    statement = select(Post).options(selectinload(Post.media_items))
    statement = _apply_filters(statement, keyword, author, has_media, start_at, end_at)

    count_statement = select(func.count()).select_from(Post)
    count_statement = _apply_filters(count_statement, keyword, author, has_media, start_at, end_at)
    total = db.scalar(count_statement) or 0

    if sort == "hot":
        statement = statement.order_by((Post.like_count + Post.repost_count + Post.reply_count + Post.view_count).desc())
    elif sort == "published_at":
        statement = statement.order_by(Post.published_at.desc())
    else:
        statement = statement.order_by(Post.crawled_at.desc())

    items = list(db.scalars(statement.offset((page - 1) * page_size).limit(page_size)))
    return PostListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{post_id}", response_model=PostRead)
def get_post(post_id: int, db: Session = Depends(get_db)) -> Post:
    post = db.get(Post, post_id, options=[selectinload(Post.media_items)])
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


def _apply_filters(
    statement: Select,
    keyword: Optional[str],
    author: Optional[str],
    has_media: Optional[bool],
    start_at: Optional[datetime],
    end_at: Optional[datetime],
) -> Select:
    if keyword:
        statement = statement.where(Post.keyword == keyword)
    if author:
        pattern = f"%{author}%"
        statement = statement.where(or_(Post.author_name.like(pattern), Post.author_handle.like(pattern)))
    if start_at:
        statement = statement.where(Post.published_at >= start_at)
    if end_at:
        statement = statement.where(Post.published_at <= end_at)
    if has_media is True:
        statement = statement.where(Post.id.in_(select(Media.post_id)))
    elif has_media is False:
        statement = statement.where(Post.id.not_in(select(Media.post_id)))
    return statement
