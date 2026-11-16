from fastapi.testclient import TestClient
from pydantic import SecretStr

import android_app  # noqa: F401 - registers the authenticated web-learning route
import main
from config import settings


def test_dashboard_contains_mobile_voice_controls():
    with TestClient(main.app) as client:
        response = client.get('/')
    assert response.status_code == 200
    assert 'SUN.AI' in response.text
    assert 'webkitSpeechRecognition' in response.text


def test_web_learning_is_pending_until_owner_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'database_path', str(tmp_path / 'web-learning.db'))
    monkeypatch.setattr(settings, 'sunai_api_token', SecretStr('test-token'))

    async def fake_search(topic, max_results):
        assert topic == 'Android browser speech'
        assert max_results == 2
        return [{
            'title': 'Browser speech docs',
            'url': 'https://example.test/speech',
            'content': 'Browser speech support varies by device.',
            'published_date': None,
        }]

    monkeypatch.setattr(android_app.research, 'search_web', fake_search)
    headers = {'Authorization': 'Bearer test-token'}
    with TestClient(main.app) as client:
        response = client.post('/api/web-learning', headers=headers, json={'topic': 'Android browser speech', 'max_results': 2})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['ai_model_used'] is False
        assert result['approval_status'] == 'pending'
        records = client.get('/api/learning', headers=headers).json()['learning_records']
        assert any(r['id'] == result['learning_record_id'] and r['approval_status'] == 'pending' for r in records)
        approved = client.patch(
            f"/api/learning/{result['learning_record_id']}/approval",
            headers=headers,
            json={'status': 'approved'},
        )
        assert approved.status_code == 200


def test_web_learning_requires_authentication():
    with TestClient(main.app) as client:
        assert client.post('/api/web-learning', json={'topic': 'test'}).status_code == 401
