from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from auth import get_current_user, get_current_user_optional
from database import get_session
from models import Gif, Like, User
from routers.gifs import count_likes

router = APIRouter(prefix="/gifs", tags=["likes"])


def _get_like(session: Session, user_id: int, gif_id: int) -> Optional[Like]:
    return session.exec(
        select(Like).where(Like.user_id == user_id, Like.gif_id == gif_id)
    ).first()


@router.post("/{gif_id}/like")
def toggle_like(
    gif_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    gif = session.get(Gif, gif_id)
    if gif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gif not found"
        )

    existing = _get_like(session, current_user.id, gif_id)
    if existing is not None:
        session.delete(existing)
        session.commit()
        liked = False
    else:
        session.add(Like(user_id=current_user.id, gif_id=gif_id))
        session.commit()
        liked = True

    return {"liked": liked, "like_count": count_likes(session, gif_id)}


@router.get("/{gif_id}/likes")
def get_likes(
    gif_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    session: Session = Depends(get_session),
):
    gif = session.get(Gif, gif_id)
    if gif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gif not found"
        )

    liked_by_me = False
    if current_user is not None:
        liked_by_me = _get_like(session, current_user.id, gif_id) is not None

    return {
        "like_count": count_likes(session, gif_id),
        "liked_by_me": liked_by_me,
    }
