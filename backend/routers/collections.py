from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from auth import get_current_user, get_current_user_optional
from database import get_session
from models import Collection, Gif, User
from routers.gifs import GifResponse, _serialize, count_likes

router = APIRouter(tags=["collections"])


def _get_collection(
    session: Session, user_id: int, gif_id: int
) -> Optional[Collection]:
    return session.exec(
        select(Collection).where(
            Collection.user_id == user_id, Collection.gif_id == gif_id
        )
    ).first()


@router.post("/gifs/{gif_id}/save")
def toggle_save(
    gif_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    gif = session.get(Gif, gif_id)
    if gif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gif not found"
        )

    existing = _get_collection(session, current_user.id, gif_id)
    if existing is not None:
        session.delete(existing)
        session.commit()
        saved = False
    else:
        session.add(Collection(user_id=current_user.id, gif_id=gif_id))
        session.commit()
        saved = True

    return {"saved": saved}


@router.get("/gifs/{gif_id}/saved")
def get_saved_status(
    gif_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: Session = Depends(get_session),
):
    gif = session.get(Gif, gif_id)
    if gif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gif not found"
        )

    saved = False
    if current_user is not None:
        saved = _get_collection(session, current_user.id, gif_id) is not None

    return {"saved": saved}


@router.get("/collections", response_model=List[GifResponse])
def list_collection(
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if page < 1:
        page = 1
    if limit < 1:
        limit = 20
    offset = (page - 1) * limit

    # Newest saves first.
    query = (
        select(Gif)
        .join(Collection, Collection.gif_id == Gif.id)
        .where(Collection.user_id == current_user.id)
        .order_by(Collection.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    gifs = session.exec(query).all()

    results: List[GifResponse] = []
    for gif in gifs:
        uploader = session.get(User, gif.user_id)
        username = uploader.username if uploader else "unknown"
        results.append(
            _serialize(gif, username, like_count=count_likes(session, gif.id))
        )
    return results
