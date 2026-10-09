from app.memory.task_history import TaskHistory


history = TaskHistory()

tasks = history.get_recent_tasks(limit=2)

print("Recent tasks:")

for task in tasks:
    print(task)