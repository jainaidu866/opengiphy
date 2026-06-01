from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from auth import get_current_user
from database import get_session
from models import Gif, Report, User

router = APIRouter(prefix="/gifs", tags=["reports"])


class ReportRequest(BaseModel):
    reason: str = Field(min_length=10)


@router.post("/{gif_id}/report")
def report_gif(
    gif_id: int,
    payload: ReportRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    gif = session.get(Gif, gif_id)
    if gif is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gif not found"
        )

    if gif.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot report your own GIF",
        )

    existing = session.exec(
        select(Report).where(
            Report.gif_id == gif_id, Report.reporter_id == current_user.id
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reported this GIF",
        )

    report = Report(
        gif_id=gif_id,
        reporter_id=current_user.id,
        reason=payload.reason,
    )
    session.add(report)
    session.commit()
    return {"message": "GIF reported successfully"}
