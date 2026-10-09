from app.memory.sqlite_memory import SQLiteMemory


def test_remember_and_recall(tmp_path):

    db_path = tmp_path / "memory.db"

    memory = SQLiteMemory(str(db_path))

    memory.remember(
        "language",
        "Python"
    )

    assert memory.recall("language") == "Python"


def test_update(tmp_path):

    db_path = tmp_path / "memory.db"

    memory = SQLiteMemory(str(db_path))

    memory.remember(
        "model",
        "Qwen2.5-1.5B"
    )

    memory.remember(
        "model",
        "Qwen2.5-3B"
    )

    assert memory.recall("model") == "Qwen2.5-3B"


def test_forget(tmp_path):

    db_path = tmp_path / "memory.db"

    memory = SQLiteMemory(str(db_path))

    memory.remember(
        "temporary",
        "hello"
    )

    memory.forget("temporary")

    assert memory.recall("temporary") is None


def test_persistence(tmp_path):

    db_path = tmp_path / "memory.db"

    memory1 = SQLiteMemory(str(db_path))

    memory1.remember(
        "persistent",
        "important information"
    )

    memory2 = SQLiteMemory(str(db_path))

    assert (
        memory2.recall("persistent")
        == "important information"
    )