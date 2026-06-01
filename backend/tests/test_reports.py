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
REASON = "This GIF contains inappropriate content."


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


def setup_gif_and_reporter(client):
    owner = auth_headers(client, "owner@example.com", "owner")
    gif_id = upload_gif(client, owner).json()["id"]
    reporter = auth_headers(client, "reporter@example.com", "reporter")
    return gif_id, owner, reporter


def test_report_gif_successfully(client):
    gif_id, _owner, reporter = setup_gif_and_reporter(client)
    response = client.post(
        f"/gifs/{gif_id}/report", headers=reporter, json={"reason": REASON}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "GIF reported successfully"}


def test_report_same_gif_twice_conflict(client):
    gif_id, _owner, reporter = setup_gif_and_reporter(client)
    client.post(f"/gifs/{gif_id}/report", headers=reporter, json={"reason": REASON})
    second = client.post(
        f"/gifs/{gif_id}/report", headers=reporter, json={"reason": REASON}
    )
    assert second.status_code == 409


def test_report_own_gif_bad_request(client):
    owner = auth_headers(client, "owner@example.com", "owner")
    gif_id = upload_gif(client, owner).json()["id"]
    response = client.post(
        f"/gifs/{gif_id}/report", headers=owner, json={"reason": REASON}
    )
    assert response.status_code == 400


def test_report_without_auth(client):
    gif_id, _owner, _reporter = setup_gif_and_reporter(client)
    response = client.post(f"/gifs/{gif_id}/report", json={"reason": REASON})
    assert response.status_code == 401


def test_report_nonexistent_gif(client):
    reporter = auth_headers(client, "reporter@example.com", "reporter")
    response = client.post(
        "/gifs/99999/report", headers=reporter, json={"reason": REASON}
    )
    assert response.status_code == 404


def test_report_reason_too_short(client):
    gif_id, _owner, reporter = setup_gif_and_reporter(client)
    response = client.post(
        f"/gifs/{gif_id}/report", headers=reporter, json={"reason": "short"}
    )
    assert response.status_code == 422
