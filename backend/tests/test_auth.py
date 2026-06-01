import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Make the backend package importable when running pytest from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import get_session  # noqa: E402
from main import app  # noqa: E402


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
def client_fixture(session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def register_user(client, email="alice@example.com", username="alice", password="secret123"):
    return client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": password},
    )


def test_register_success(client):
    response = register_user(client)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["username"] == "alice"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client):
    register_user(client)
    response = register_user(client, username="alice2")
    assert response.status_code == 409
    assert "email" in response.json()["detail"]


def test_register_duplicate_username(client):
    register_user(client)
    response = register_user(client, email="other@example.com")
    assert response.status_code == 409
    assert "username" in response.json()["detail"]


def test_login_success(client):
    register_user(client)
    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


def test_login_wrong_password(client):
    register_user(client)
    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401


def test_protected_route_without_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_protected_route_with_valid_token(client):
    register_user(client)
    login = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "secret123"},
    )
    token = login.json()["access_token"]
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_protected_route_with_invalid_token(client):
    response = client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401
