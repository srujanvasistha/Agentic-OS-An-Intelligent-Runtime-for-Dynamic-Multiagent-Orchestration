from app.memory.sqlite_memory import SQLiteMemory


memory = SQLiteMemory()


memory.remember(
    "user_name",
    "John",
    source="user"
)


print(
    "User name:",
    memory.recall("user_name")
)

memory.remember(
    "temporary",
    "delete me"
)

print(
    "Before delete:",
    memory.recall("temporary")
)

memory.forget("temporary")

print(
    "After delete:",
    memory.recall("temporary")
)

memory.remember(
    "language",
    "Python",
    source="user"
)

memory.remember(
    "model",
    "Qwen2.5-1.5B",
    source="system"
)

print("\nRecent memories:")

for row in memory.get_recent():
    print(row)