import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
import main
from config import settings

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test_sunai.db"))
    monkeypatch.setattr(settings, "sunai_api_token", SecretStr("test-token"))
    with TestClient(main.app) as test_client:
        yield test_client

def auth_headers():
    return {"Authorization": "Bearer test-token"}

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_dashboard_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "SUN.AI Advanced" in response.text

def test_memory_endpoint_requires_authentication(client):
    assert client.get("/api/memory").status_code == 401

def test_save_and_list_memory(client):
    saved = client.post("/api/memory", headers=auth_headers(), json={"content": "The user prefers concise answers."})
    assert saved.status_code == 200
    assert saved.json()["id"] == saved.json()["memory_id"]
    listed = client.get("/api/memory", headers=auth_headers())
    assert listed.status_code == 200
    assert any(m["content"] == "The user prefers concise answers." for m in listed.json()["memories"])

def test_memory_search(client):
    client.post("/api/memory", headers=auth_headers(), json={"content": "The project uses FastAPI and SQLite."})
    result = client.get("/api/memory/search", headers=auth_headers(), params={"q": "FastAPI"})
    assert result.status_code == 200
    assert any("FastAPI" in m["content"] for m in result.json()["memories"])

def test_feedback_and_learning_summary(client):
    response = client.post("/api/feedback", headers=auth_headers(), json={"message": "Helpful answer", "rating": 5})
    assert response.status_code == 200
    summary = client.get("/api/learning", headers=auth_headers())
    assert summary.status_code == 200
    assert summary.json()["feedback_summary"]["count"] == 1
    assert isinstance(summary.json()["learning_records"], list)

def test_learning_record(client):
    response = client.post("/api/learning", headers=auth_headers(), json={"topic": "FastAPI", "summary": "Use lifespan for startup work."})
    assert response.status_code == 200
    assert client.get("/api/learning", headers=auth_headers()).json()["learning_records"]

def test_proposals_require_authentication(client):
    assert client.get("/api/improvements").status_code == 401

def test_create_and_list_proposal(client):
    response = client.post("/api/improvements/propose", headers=auth_headers(), json={"title": "Proposal", "description": "Test syntax", "target_file": "agent.py", "proposed_code": "def hello():\n    return 'hi'\n"})
    assert response.status_code == 200
    listed = client.get("/api/improvements", headers=auth_headers())
    assert listed.status_code == 200
    assert len(listed.json()["proposals"]) == 1

def test_languages_endpoint(client):
    response = client.get("/api/languages")
    assert response.status_code == 200
    data = response.json()
    assert set(data["languages"]) == {"english", "hindi", "telugu", "kannada", "lambani"}
    assert data["lambani"] == "experimental-text-only"


def test_chat_language_selection_is_passed_to_ai(client, monkeypatch):
    async def fake_ask_ai(prompt, memories=None, learning_context=None, language="english"):
        assert language == "kannada"
        return "ನಮಸ್ಕಾರ"
    monkeypatch.setattr(main, "ask_ai", fake_ask_ai)
    response = client.post(
        "/api/chat",
        headers=auth_headers(),
        json={"prompt": "ನಮಸ್ಕಾರ", "language": "kannada", "speech_locale": "hi-IN"},
    )
    assert response.status_code == 200
    assert response.json()["language"] == "kannada"
    assert response.json()["response"] == "ನಮಸ್ಕಾರ"


def test_chat_auto_language_uses_browser_locale(client, monkeypatch):
    async def fake_ask_ai(prompt, memories=None, learning_context=None, language="english"):
        assert language == "telugu"
        return "నమస్కారం"
    monkeypatch.setattr(main, "ask_ai", fake_ask_ai)
    response = client.post(
        "/api/chat",
        headers=auth_headers(),
        json={"prompt": "నమస్కారం", "language": "auto", "speech_locale": "te-IN"},
    )
    assert response.status_code == 200
    assert response.json()["language"] == "telugu"
