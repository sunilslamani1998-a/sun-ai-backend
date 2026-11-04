import sqlite3
import database


def test_language_migration_is_repeatable_and_preserves_old_data(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    monkeypatch.setattr(database.settings, "database_path", str(db_path))
    c = sqlite3.connect(db_path)
    c.executescript("""
        CREATE TABLE memories (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, content TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'general', importance INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE learning_records (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, topic TEXT NOT NULL, summary TEXT NOT NULL, source TEXT, created_at TEXT NOT NULL);
        INSERT INTO memories(user_id,content,created_at,updated_at) VALUES('owner','ಹಳೆಯ ನೆನಪು','2026-01-01','2026-01-01');
        INSERT INTO learning_records(user_id,topic,summary,created_at) VALUES('owner','ವಿಷಯ','ಸಾರಾಂಶ','2026-01-01');
    """)
    c.commit(); c.close()
    database.init_db()
    database.init_db()
    memories = database.get_memories("owner")
    records = database.get_learning_records("owner")
    assert memories[0]["content"] == "ಹಳೆಯ ನೆನಪು"
    assert memories[0]["language"] == "english"
    assert records[0]["summary"] == "ಸಾರಾಂಶ"
    assert records[0]["language"] == "english"
