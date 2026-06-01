from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_session
from models import Gif, User
from routers.gifs import GifResponse, _serialize, count_likes

router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfileResponse(BaseModel):
    username: str
    created_at: datetime
    gifs: List[GifResponse]


@router.get("/{username}", response_model=ProfileResponse)
def get_profile(
    username: str,
    page: int = 1,
    limit: int = 20,
    session: Session = Depends(get_session),
):
    user = session.exec(
        select(User).where(User.username == username)
    ).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if page < 1:
        page = 1
    if limit < 1:
        limit = 20
    offset = (page - 1) * limit

    gifs = session.exec(
        select(Gif)
        .where(Gif.user_id == user.id)
        .order_by(Gif.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return ProfileResponse(
        username=user.username,
        created_at=user.created_at,
        gifs=[
            _serialize(gif, user.username, like_count=count_likes(session, gif.id))
            for gif in gifs
        ],
    )
