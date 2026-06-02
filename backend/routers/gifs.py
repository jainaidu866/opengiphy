import json
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy import Text, cast, func, or_
from sqlmodel import Session, select

from auth import get_current_user
from constants import CATEGORIES
from database import get_session
from models import Gif, Like, User

TRENDING_WINDOW_DAYS = 7

router = APIRouter(prefix="/gifs", tags=["gifs"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")


class GifResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    tags: List[str] = []
    category: Optional[str] = None
    file_path: str
    url: str
    view_count: int
    like_count: int = 0
    created_at: datetime
    uploader_username: str


def count_likes(session: Session, gif_id: int) -> int:
    return session.exec(
        select(func.count()).select_from(Like).where(Like.gif_id == gif_id)
    ).one()


def _parse_tags(raw: Optional[str]) -> List[str]:
    """Accept tags as a JSON list string or a comma-separated string."""
    if not raw:
        return []
    raw = raw.strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(t) for t in parsed]
        return [str(parsed)]
    except json.JSONDecodeError:
        return [t.strip() for t in raw.split(",") if t.strip()]


def _serialize(gif: Gif, username: str, like_count: int = 0) -> GifResponse:
    filename = os.path.basename(gif.file_path)
    return GifResponse(
        id=gif.id,
        user_id=gif.user_id,
        title=gif.title,
        description=gif.description,
        tags=gif.tags or [],
        category=gif.category,
        file_path=gif.file_path,
        url=f"/uploads/{filename}",
        view_count=gif.view_count,
        like_count=like_count,
        created_at=gif.created_at,
        uploader_username=username,
    )


@router.post(
    "/upload",
    response_model=GifResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_gif(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    filename = file.filename or ""
    is_gif_ext = filename.lower().endswith(".gif")
    is_gif_type = (file.content_type or "").lower() in ("image/gif", "")
    if not is_gif_ext or not is_gif_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .gif files are allowed",
        )

    # Category is optional, but if provided it must be one of the fixed set.
    category = (category or "").strip() or None
    if category is not None and category not in CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {', '.join(CATEGORIES)}",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}.gif"
    disk_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(disk_path, "wb") as out:
        out.write(file.file.read())

    gif = Gif(
        user_id=current_user.id,
        title=title,
        description=description,
        tags=_parse_tags(tags),
        category=category,
        file_path=disk_path.replace("\\", "/"),
    )
    session.add(gif)
    session.commit()
    session.refresh(gif)
    return _serialize(gif, current_user.username, like_count=0)


@router.get("/", response_model=List[GifResponse])
def list_gifs(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    category: Optional[str] = None,
    sort: str = "new",
    session: Session = Depends(get_session),
):
    if page < 1:
        page = 1
    if limit < 1:
        limit = 20
    offset = (page - 1) * limit

    query = select(Gif)
    if category and category.strip():
        query = query.where(Gif.category == category.strip())
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Gif.title.ilike(pattern),
                Gif.description.ilike(pattern),
                # tags is a JSON column — match against its text form so
                # a tag like "cat" is found. Portable across SQLite/Postgres.
                cast(Gif.tags, Text).ilike(pattern),
            )
        )

    if sort == "trending":
        # Correlated like-count per gif; score = likes*2 + views, restricted
        # to the recent window. Portable across SQLite/Postgres.
        like_count_expr = (
            select(func.count(Like.user_id))
            .where(Like.gif_id == Gif.id)
            .correlate(Gif)
            .scalar_subquery()
        )
        score = like_count_expr * 2 + Gif.view_count
        cutoff = datetime.utcnow() - timedelta(days=TRENDING_WINDOW_DAYS)
        query = query.where(Gif.created_at >= cutoff).order_by(
            score.desc(), Gif.created_at.desc()
        )
    else:
        query = query.order_by(Gif.created_at.desc())

    gifs = session.exec(query.offset(offset).limit(limit)).all()

    results: List[GifResponse] = []
    for gif in gifs:
        uploader = session.get(User, gif.user_id)
        username = uploader.username if uploader else "unknown"
        results.append(
            _serialize(gif, username, like_count=count_likes(session, gif.id))
        )
    return results


@router.get("/{gif_id}", response_model=GifResponse)
def get_gif(gif_id: int, session: Session = Depends(get_session)):
    gif = session.get(Gif, gif_id)
    if gif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gif not found"
        )

    gif.view_count += 1
    session.add(gif)
    session.commit()
    session.refresh(gif)

    uploader = session.get(User, gif.user_id)
    username = uploader.username if uploader else "unknown"
    return _serialize(gif, username, like_count=count_likes(session, gif.id))


@router.get("/{gif_id}/related", response_model=List[GifResponse])
def related_gifs(
    gif_id: int,
    limit: int = 6,
    session: Session = Depends(get_session),
):
    gif = session.get(Gif, gif_id)
    if gif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gif not found"
        )

    if limit < 1:
        limit = 6

    tags = gif.tags or []
    if not tags:
        return []

    # Broad candidate filter: any other GIF whose tag-text mentions one of our
    # tags (portable JSON-as-text match across SQLite/Postgres). Exact overlap
    # is computed in Python below for accurate ranking.
    conditions = [cast(Gif.tags, Text).ilike(f"%{tag}%") for tag in tags]
    query = select(Gif).where(Gif.id != gif_id).where(or_(*conditions))
    candidates = session.exec(query).all()

    our_tags = {t.lower() for t in tags}
    scored: List[tuple[int, Gif]] = []
    for cand in candidates:
        shared = len({t.lower() for t in (cand.tags or [])} & our_tags)
        if shared > 0:
            scored.append((shared, cand))

    # Most shared tags first; tie-break by recency (newest first).
    scored.sort(key=lambda pair: (pair[0], pair[1].created_at), reverse=True)

    results: List[GifResponse] = []
    for _shared, cand in scored[:limit]:
        uploader = session.get(User, cand.user_id)
        username = uploader.username if uploader else "unknown"
        results.append(
            _serialize(cand, username, like_count=count_likes(session, cand.id))
        )
    return results


@router.delete("/{gif_id}")
def delete_gif(
    gif_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    gif = session.get(Gif, gif_id)
    if gif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gif not found"
        )
    if gif.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own gifs",
        )

    if os.path.exists(gif.file_path):
        try:
            os.remove(gif.file_path)
        except OSError:
            pass

    session.delete(gif)
    session.commit()
    return {"message": "Gif deleted successfully"}
