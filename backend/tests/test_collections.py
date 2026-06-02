import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routers.gifs as gifs_module  # noqa: E402
from database import get_session  # noqa: E402
from main import app  # noqa: E402

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


def upload_gif(client, headers, title="My GIF"):
    return client.post(
        "/gifs/upload",
        headers=headers,
        data={"title": title, "description": "a test gif", "tags": "[]"},
        files={"file": ("test.gif", GIF_BYTES, "image/gif")},
    )


def test_save_toggles_on_and_off(client):
    headers = auth_headers(client)
    gif_id = upload_gif(client, headers).json()["id"]

    on = client.post(f"/gifs/{gif_id}/save", headers=headers)
    assert on.status_code == 200
    assert on.json()["saved"] is True

    off = client.post(f"/gifs/{gif_id}/save", headers=headers)
    assert off.status_code == 200
    assert off.json()["saved"] is False


def test_saved_status_reflects_save(client):
    headers = auth_headers(client)
    gif_id = upload_gif(client, headers).json()["id"]

    before = client.get(f"/gifs/{gif_id}/saved", headers=headers)
    assert before.json()["saved"] is False

    client.post(f"/gifs/{gif_id}/save", headers=headers)
    after = client.get(f"/gifs/{gif_id}/saved", headers=headers)
    assert after.json()["saved"] is True


def test_collection_lists_saved_gifs(client):
    headers = auth_headers(client)
    a_id = upload_gif(client, headers, title="A").json()["id"]
    b_id = upload_gif(client, headers, title="B").json()["id"]

    client.post(f"/gifs/{a_id}/save", headers=headers)

    resp = client.get("/collections", headers=headers)
    assert resp.status_code == 200
    ids = [g["id"] for g in resp.json()]
    assert a_id in ids
    assert b_id not in ids


def test_collection_requires_auth(client):
    resp = client.get("/collections")
    assert resp.status_code == 401


def test_save_requires_auth(client):
    headers = auth_headers(client)
    gif_id = upload_gif(client, headers).json()["id"]

    resp = client.post(f"/gifs/{gif_id}/save")
    assert resp.status_code == 401


def test_save_404_on_missing_gif(client):
    headers = auth_headers(client)
    resp = client.post("/gifs/99999/save", headers=headers)
    assert resp.status_code == 404
