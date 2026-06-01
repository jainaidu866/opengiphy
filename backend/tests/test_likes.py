import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

# Make the backend package importable when running pytest from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routers.gifs as gifs_module  # noqa: E402
from database import get_session  # noqa: E402
from main import app  # noqa: E402
from models import Like  # noqa: E402

GIF_BYTES = b"GIF89a" + b"\x00" * 32


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session, tmp_path, monkeypatch):
    monkeypatch.setattr(gifs_module, "UPLOAD_DIR", str(tmp_path))

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def auth_headers(client, email="bob@example.com", username="bob", password="secret123"):
    client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    login = client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload_gif(client, headers, title="My GIF", tags='["funny"]'):
    return client.post(
        "/gifs/upload",
        headers=headers,
        data={"title": title, "description": "", "tags": tags},
        files={"file": ("test.gif", GIF_BYTES, "image/gif")},
    )


def test_like_a_gif(client):
    headers = auth_headers(client)
    gif_id = upload_gif(client, headers).json()["id"]

    response = client.post(f"/gifs/{gif_id}/like", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"liked": True, "like_count": 1}


def test_unlike_toggle(client):
    headers = auth_headers(client)
    gif_id = upload_gif(client, headers).json()["id"]

    client.post(f"/gifs/{gif_id}/like", headers=headers)  # like
    response = client.post(f"/gifs/{gif_id}/like", headers=headers)  # unlike
    assert response.status_code == 200
    assert response.json() == {"liked": False, "like_count": 0}


def test_like_is_idempotent_single_row(client, session):
    # The composite PK (user_id, gif_id) guarantees a user can never
    # accumulate more than one like row for a gif.
    headers = auth_headers(client)
    gif_id = upload_gif(client, headers).json()["id"]

    client.post(f"/gifs/{gif_id}/like", headers=headers)
    rows = session.exec(select(Like).where(Like.gif_id == gif_id)).all()
    assert len(rows) == 1

    # A second distinct user liking adds exactly one more — no inflation.
    other = auth_headers(client, email="eve@example.com", username="eve")
    response = client.post(f"/gifs/{gif_id}/like", headers=other)
    assert response.json()["like_count"] == 2


def test_get_like_count_without_auth(client):
    headers = auth_headers(client)
    gif_id = upload_gif(client, headers).json()["id"]
    client.post(f"/gifs/{gif_id}/like", headers=headers)

    response = client.get(f"/gifs/{gif_id}/likes")
    assert response.status_code == 200
    assert response.json() == {"like_count": 1, "liked_by_me": False}


def test_liked_by_me_true_when_liked(client):
    headers = auth_headers(client)
    gif_id = upload_gif(client, headers).json()["id"]
    client.post(f"/gifs/{gif_id}/like", headers=headers)

    response = client.get(f"/gifs/{gif_id}/likes", headers=headers)
    assert response.json() == {"like_count": 1, "liked_by_me": True}


def test_liked_by_me_false_when_not_liked(client):
    headers = auth_headers(client)
    gif_id = upload_gif(client, headers).json()["id"]

    response = client.get(f"/gifs/{gif_id}/likes", headers=headers)
    assert response.json() == {"like_count": 0, "liked_by_me": False}


def test_like_nonexistent_gif_404(client):
    headers = auth_headers(client)
    response = client.post("/gifs/99999/like", headers=headers)
    assert response.status_code == 404


def test_like_requires_auth(client):
    headers = auth_headers(client)
    gif_id = upload_gif(client, headers).json()["id"]
    response = client.post(f"/gifs/{gif_id}/like")
    assert response.status_code == 401
