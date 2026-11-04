import sqlite3

import database
import learning
import main
from fastapi.testclient import TestClient
from config import settings
from pydantic import SecretStr
import pytest


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "approval.db"))
    database.init_db()


def test_new_learning_record_waits_for_approval(isolated_db):
    record_id = learning.save_learning_record("owner", "Solar energy", "Solar panels convert sunlight into electricity.")
    records = learning.get_learning_history("owner")
    assert records[0]["id"] == record_id
    assert records[0]["approval_status"] == "pending"
    assert learning.build_learning_context("owner") == []


def test_approved_learning_record_enters_context(isolated_db):
    record_id = learning.save_learning_record("owner", "Python", "Python is a programming language.", language="english")
    assert learning.review_learning_record("owner", record_id, "approved") is True
    context = learning.build_learning_context("owner")
    assert len(context) == 1
    assert "Python is a programming language" in context[0]
    assert learning.get_learning_history("owner")[0]["approved_at"]


def test_rejected_learning_record_never_enters_context(isolated_db):
    record_id = learning.save_learning_record("owner", "Bad claim", "Unverified content")
    assert learning.review_learning_record("owner", record_id, "rejected") is True
    assert learning.build_learning_context("owner") == []


def test_approval_is_owner_scoped_and_only_pending_once(isolated_db):
    record_id = learning.save_learning_record("owner-a", "Topic", "Summary")
    assert learning.review_learning_record("owner-b", record_id, "approved") is False
    assert learning.review_learning_record("owner-a", record_id, "approved") is True
    assert learning.review_learning_record("owner-a", record_id, "rejected") is False


def test_legacy_learning_rows_remain_approved(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    monkeypatch.setattr(database.settings, "database_path", str(db_path))
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE learning_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            topic TEXT NOT NULL, summary TEXT NOT NULL, source TEXT, created_at TEXT NOT NULL
        );
        INSERT INTO learning_records(user_id,topic,summary,created_at)
        VALUES('owner','Old topic','Old saved content','2026-01-01');
    """)
    conn.commit()
    conn.close()
    database.init_db()
    database.init_db()
    rows = database.get_learning_records("owner")
    assert rows[0]["approval_status"] == "approved"
    assert learning.build_learning_context("owner")


def test_learning_approval_api_requires_owner_auth(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "api.db"))
    monkeypatch.setattr(settings, "sunai_api_token", SecretStr("test-token"))
    with TestClient(main.app) as client:
        created = client.post("/api/learning", headers={"Authorization": "Bearer test-token"}, json={"topic": "Kannada", "summary": "ಕನ್ನಡ ಭಾಷೆ"})
        assert created.status_code == 200
        record_id = created.json()["learning_record_id"]
        assert created.json()["approval_status"] == "pending"
        reviewed = client.patch(f"/api/learning/{record_id}/approval", headers={"Authorization": "Bearer test-token"}, json={"status": "approved"})
        assert reviewed.status_code == 200
        assert reviewed.json()["approval_status"] == "approved"
        assert client.patch(f"/api/learning/{record_id}/approval", headers={"Authorization": "Bearer wrong"}, json={"status": "rejected"}).status_code == 401
