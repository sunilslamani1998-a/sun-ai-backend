import database
import memory
import learning


def test_kannada_memory_persists_and_can_be_searched(tmp_path, monkeypatch):
    monkeypatch.setattr(database.settings, "database_path", str(tmp_path / "memory.db"))
    database.init_db()
    memory.save_memory("owner", "ನನಗೆ ಕನ್ನಡ ಇಷ್ಟ", language="kannada")
    rows = memory.list_memories("owner")
    assert rows[0]["language"] == "kannada"
    assert memory.search_memories("owner", "ಕನ್ನಡ")


def test_lambani_learning_record_preserves_language(tmp_path, monkeypatch):
    monkeypatch.setattr(database.settings, "database_path", str(tmp_path / "learning.db"))
    database.init_db()
    learning.save_learning_record("owner", "Lambani", "User-provided vocabulary", language="lambani")
    rows = learning.get_learning_history("owner")
    assert rows[0]["language"] == "lambani"
