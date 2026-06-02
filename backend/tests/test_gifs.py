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
    # Isolate uploads to a temp dir so tests don't touch the real ./uploads.
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
    login = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload_gif(client, headers=None, title="My GIF", tags='["funny", "cat"]'):
    if headers is None:
        headers = auth_headers(client)
    return client.post(
        "/gifs/upload",
        headers=headers,
        data={"title": title, "description": "a test gif", "tags": tags},
        files={"file": ("test.gif", GIF_BYTES, "image/gif")},
    )


def test_upload_gif_success(client, tmp_path):
    headers = auth_headers(client)
    response = upload_gif(client)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My GIF"
    assert data["tags"] == ["funny", "cat"]
    assert data["uploader_username"] == "bob"
    assert data["view_count"] == 0
    assert data["url"].startswith("/uploads/")
    # File actually landed on disk in the temp upload dir.
    assert os.path.exists(data["file_path"])


def test_upload_requires_auth(client):
    response = upload_gif(client, headers={})
    assert response.status_code == 401


def test_upload_rejects_non_gif(client):
    headers = auth_headers(client)
    response = client.post(
        "/gifs/upload",
        headers=headers,
        data={"title": "bad", "tags": "[]"},
        files={"file": ("note.txt", b"not a gif", "text/plain")},
    )
    assert response.status_code == 400


def test_list_gifs_paginated(client):
    headers = auth_headers(client)
    for i in range(3):
        upload_gif(client, headers, title=f"gif-{i}")

    page1 = client.get("/gifs/?page=1&limit=2")
    assert page1.status_code == 200
    assert len(page1.json()) == 2

    page2 = client.get("/gifs/?page=2&limit=2")
    assert page2.status_code == 200
    assert len(page2.json()) == 1


def test_search_filters_by_title_and_tags(client):
    headers = auth_headers(client)
    upload_gif(client, headers, title="Dancing Cat", tags='["funny", "cat"]')
    upload_gif(client, headers, title="Happy Dog", tags='["dog"]')

    # Match on title
    by_title = client.get("/gifs/?search=dancing")
    assert by_title.status_code == 200
    assert [g["title"] for g in by_title.json()] == ["Dancing Cat"]

    # Match on a tag
    by_tag = client.get("/gifs/?search=dog")
    assert [g["title"] for g in by_tag.json()] == ["Happy Dog"]

    # No match
    assert client.get("/gifs/?search=zzzz").json() == []


def test_trending_sort_ranks_by_score(client):
    headers = auth_headers(client)
    a_id = upload_gif(client, headers, title="A").json()["id"]
    b_id = upload_gif(client, headers, title="B").json()["id"]

    # A: 1 like -> score = 1*2 + 0 views = 2
    client.post(f"/gifs/{a_id}/like", headers=headers)
    # B: 3 views (each GET increments) -> score = 0*2 + 3 = 3
    for _ in range(3):
        client.get(f"/gifs/{b_id}")

    trending = client.get("/gifs/?sort=trending")
    assert trending.status_code == 200
    titles = [g["title"] for g in trending.json()]
    assert titles[:2] == ["B", "A"]  # B outranks A on score


def test_get_single_gif_increments_view_count(client):
    headers = auth_headers(client)
    gif_id = upload_gif(client).json()["id"]

    first = client.get(f"/gifs/{gif_id}")
    assert first.status_code == 200
    assert first.json()["view_count"] == 1

    second = client.get(f"/gifs/{gif_id}")
    assert second.json()["view_count"] == 2


def test_delete_gif_as_owner(client):
    headers = auth_headers(client)
    upload = upload_gif(client)
    gif_id = upload.json()["id"]
    file_path = upload.json()["file_path"]

    response = client.delete(f"/gifs/{gif_id}", headers=headers)
    assert response.status_code == 200
    assert "message" in response.json()
    # Record gone and file removed from disk.
    assert client.get(f"/gifs/{gif_id}").status_code == 404
    assert not os.path.exists(file_path)


def test_delete_gif_as_non_owner(client):
    owner_headers = auth_headers(client)
    gif_id = upload_gif(client).json()["id"]

    other_headers = auth_headers(
        client, email="eve@example.com", username="eve"
    )
    response = client.delete(f"/gifs/{gif_id}", headers=other_headers)
    assert response.status_code == 403


def test_delete_gif_without_auth(client):
    auth_headers(client)
    gif_id = upload_gif(client).json()["id"]

    response = client.delete(f"/gifs/{gif_id}")
    assert response.status_code == 401


def test_related_returns_tag_sharing_gifs_excluding_self(client):
    headers = auth_headers(client)
    base = upload_gif(client, headers, title="Base", tags='["cat", "funny"]').json()
    shares = upload_gif(client, headers, title="Shares", tags='["cat", "cute"]').json()
    upload_gif(client, headers, title="Unrelated", tags='["dog"]')

    resp = client.get(f"/gifs/{base['id']}/related")
    assert resp.status_code == 200
    ids = [g["id"] for g in resp.json()]
    # Includes the tag-sharing GIF, excludes self and the unrelated one.
    assert shares["id"] in ids
    assert base["id"] not in ids
    titles = [g["title"] for g in resp.json()]
    assert "Unrelated" not in titles


def test_related_orders_by_shared_tag_count(client):
    headers = auth_headers(client)
    base = upload_gif(
        client, headers, title="Base", tags='["cat", "funny", "cute"]'
    ).json()
    # two shared tags
    two = upload_gif(client, headers, title="Two", tags='["cat", "funny"]').json()
    # one shared tag
    one = upload_gif(client, headers, title="One", tags='["cat", "sports"]').json()

    resp = client.get(f"/gifs/{base['id']}/related")
    ids = [g["id"] for g in resp.json()]
    assert ids[0] == two["id"]
    assert ids[1] == one["id"]


def test_related_respects_limit(client):
    headers = auth_headers(client)
    base = upload_gif(client, headers, title="Base", tags='["cat"]').json()
    for i in range(4):
        upload_gif(client, headers, title=f"rel-{i}", tags='["cat"]')

    resp = client.get(f"/gifs/{base['id']}/related?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_related_empty_when_no_tags(client):
    headers = auth_headers(client)
    base = upload_gif(client, headers, title="NoTags", tags="[]").json()
    upload_gif(client, headers, title="Other", tags='["cat"]')

    resp = client.get(f"/gifs/{base['id']}/related")
    assert resp.status_code == 200
    assert resp.json() == []


def test_related_404_for_missing_gif(client):
    resp = client.get("/gifs/99999/related")
    assert resp.status_code == 404


def test_upload_with_valid_category(client):
    headers = auth_headers(client)
    resp = client.post(
        "/gifs/upload",
        headers=headers,
        data={"title": "Cat", "tags": "[]", "category": "animals"},
        files={"file": ("test.gif", GIF_BYTES, "image/gif")},
    )
    assert resp.status_code == 201
    assert resp.json()["category"] == "animals"


def test_upload_with_invalid_category_rejected(client):
    headers = auth_headers(client)
    resp = client.post(
        "/gifs/upload",
        headers=headers,
        data={"title": "Cat", "tags": "[]", "category": "not-a-category"},
        files={"file": ("test.gif", GIF_BYTES, "image/gif")},
    )
    assert resp.status_code == 400


def test_upload_without_category_allowed(client):
    headers = auth_headers(client)
    resp = upload_gif(client, headers)
    assert resp.status_code == 201
    assert resp.json()["category"] is None


def test_list_filtered_by_category(client):
    headers = auth_headers(client)
    client.post(
        "/gifs/upload",
        headers=headers,
        data={"title": "Sporty", "tags": "[]", "category": "sports"},
        files={"file": ("test.gif", GIF_BYTES, "image/gif")},
    )
    client.post(
        "/gifs/upload",
        headers=headers,
        data={"title": "Foody", "tags": "[]", "category": "food"},
        files={"file": ("test.gif", GIF_BYTES, "image/gif")},
    )

    sports = client.get("/gifs/?category=sports")
    assert sports.status_code == 200
    assert [g["title"] for g in sports.json()] == ["Sporty"]

    food = client.get("/gifs/?category=food")
    assert [g["title"] for g in food.json()] == ["Foody"]
