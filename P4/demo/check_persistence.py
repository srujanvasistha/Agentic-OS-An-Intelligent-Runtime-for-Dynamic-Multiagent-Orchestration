from app.memory.sqlite_memory import SQLiteMemory

memory = SQLiteMemory()

print(
    "Stored user:",
    memory.recall("user_name")
)