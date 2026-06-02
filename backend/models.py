from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Gif(SQLModel, table=True):
    __tablename__ = "gifs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    category: Optional[str] = Field(default=None, index=True)
    file_path: str
    view_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Like(SQLModel, table=True):
    __tablename__ = "likes"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    gif_id: int = Field(foreign_key="gifs.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Collection(SQLModel, table=True):
    __tablename__ = "collections"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    gif_id: int = Field(foreign_key="gifs.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Report(SQLModel, table=True):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("gif_id", "reporter_id", name="uq_report_gif_reporter"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    gif_id: int = Field(foreign_key="gifs.id", index=True)
    reporter_id: int = Field(foreign_key="users.id", index=True)
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
