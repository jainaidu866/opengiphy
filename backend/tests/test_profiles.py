import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Make the backend package importable when running pytest from anywhere.
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


def auth_headers(client, email, username, password="secret123"):
    client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    login = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def upload_gif(client, headers, title="My GIF"):
    return client.post(
        "/gifs/upload",
        headers=headers,
        data={"title": title, "description": "", "tags": "[]"},
        files={"file": ("test.gif", GIF_BYTES, "image/gif")},
    )


def test_get_existing_profile(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    upload_gif(client, headers, title="Alice GIF 1")
    upload_gif(client, headers, title="Alice GIF 2")

    response = client.get("/profiles/alice")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice"
    assert "created_at" in data
    assert len(data["gifs"]) == 2
    assert {g["title"] for g in data["gifs"]} == {"Alice GIF 1", "Alice GIF 2"}
    assert all(g["uploader_username"] == "alice" for g in data["gifs"])


def test_get_nonexistent_profile_404(client):
    response = client.get("/profiles/ghost")
    assert response.status_code == 404


def test_profile_shows_only_own_gifs(client):
    alice = auth_headers(client, "alice@example.com", "alice")
    bob = auth_headers(client, "bob@example.com", "bob")
    upload_gif(client, alice, title="Alice GIF")
    upload_gif(client, bob, title="Bob GIF")

    alice_profile = client.get("/profiles/alice").json()
    assert [g["title"] for g in alice_profile["gifs"]] == ["Alice GIF"]

    bob_profile = client.get("/profiles/bob").json()
    assert [g["title"] for g in bob_profile["gifs"]] == ["Bob GIF"]


def test_profile_pagination(client):
    headers = auth_headers(client, "alice@example.com", "alice")
    for i in range(3):
        upload_gif(client, headers, title=f"gif-{i}")

    page1 = client.get("/profiles/alice?page=1&limit=2").json()
    assert len(page1["gifs"]) == 2
    page2 = client.get("/profiles/alice?page=2&limit=2").json()
    assert len(page2["gifs"]) == 1
