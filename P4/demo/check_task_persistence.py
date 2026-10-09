from app.memory.task_history import TaskHistory


history = TaskHistory()


task = history.get_task("task-002")


print("Stored task:")
print(task)