import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

import main
from config import settings


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Use an isolated SQLite database and test token for every test.
    The app lifespan initializes the database.
    """
    test_db = tmp_path / "test_sunai.db"

    monkeypatch.setattr(
        settings,
        "database_path",
        str(test_db),
    )

    monkeypatch.setattr(
        settings,
        "sunai_api_token",
        SecretStr("test-token"),
    )

    with TestClient(main.app) as test_client:
        yield test_client


def auth_headers():
    return {
        "Authorization": "Bearer test-token",
    }


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"


def test_memory_endpoint_requires_authentication(client):
    response = client.get("/api/memory")

    assert response.status_code == 401


def test_save_and_list_memory(client):
    save_response = client.post(
        "/api/memory",
        headers=auth_headers(),
        json={
            "content": "The user prefers concise answers.",
        },
    )

    assert save_response.status_code == 200

    saved_data = save_response.json()
    assert "memory_id" in saved_data

    list_response = client.get(
        "/api/memory",
        headers=auth_headers(),
    )

    assert list_response.status_code == 200

    data = list_response.json()
    assert "memories" in data
    memories = data["memories"]
    assert isinstance(memories, list)
    assert any(
        item["content"] == "The user prefers concise answers."
        for item in memories
    )


def test_memory_search(client):
    client.post(
        "/api/memory",
        headers=auth_headers(),
        json={
            "content": "The project uses FastAPI and SQLite.",
        },
    )

    response = client.get(
        "/api/memory/search",
        headers=auth_headers(),
        params={
            "q": "FastAPI",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert "memories" in data
    results = data["memories"]
    assert isinstance(results, list)
    assert any(
        "FastAPI" in item["content"]
        for item in results
    )


def test_feedback_endpoint(client):
    response = client.post(
        "/api/feedback",
        headers=auth_headers(),
        json={
            "message": "The answer was useful.",
            "rating": 5,
        },
    )

    assert response.status_code == 200


def test_learning_endpoint(client):
    response = client.get(
        "/api/learning",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_proposals_endpoint_requires_authentication(client):
    response = client.get("/api/improvements")

    assert response.status_code == 401


def test_proposals_endpoint(client):
    response = client.get(
        "/api/improvements",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert "proposals" in data
    assert isinstance(data["proposals"], list)
