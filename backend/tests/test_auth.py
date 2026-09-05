import pytest
from fastapi.testclient import TestClient

from app.api.auth import get_db
from app.main import app


@pytest.fixture
def client(database_session):
    app.dependency_overrides[get_db] = lambda: database_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def auth_header(client, email, password):
    response = login(client, email, password)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_valid_login_returns_token(client):
    response = login(client, "editor@example.com", "peblo-dev-password")

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_invalid_password_is_rejected(client):
    response = login(client, "editor@example.com", "wrong-password")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_missing_authentication_is_rejected(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/auth/me", headers={"Authorization": "Bearer definitely-not-a-jwt"}
    )

    assert response.status_code == 401


def test_editor_can_access_editor_endpoint(client):
    response = client.get(
        "/auth/editor-check",
        headers=auth_header(client, "editor@example.com", "peblo-dev-password"),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "editor"
    assert "password_hash" not in response.json()


def test_editor_cannot_access_admin_endpoint(client):
    response = client.get(
        "/auth/admin-check",
        headers=auth_header(client, "editor@example.com", "peblo-dev-password"),
    )

    assert response.status_code == 403


def test_admin_can_access_admin_endpoint(client):
    response = client.get(
        "/auth/admin-check",
        headers=auth_header(client, "admin@example.com", "peblo-dev-password"),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
