from app.memory.task_history import TaskHistory


history = TaskHistory()


task_id = "task-002"


history.create_task(
    task_id,
    "Calculate current CPU usage"
)

print("Task created:")
print(history.get_task(task_id))


history.update_status(
    task_id,
    "running"
)

print("\nTask running:")
print(history.get_task(task_id))


history.save_result(
    task_id,
    "CPU usage was 35%"
)

history.update_status(
    task_id,
    "completed"
)

print("\nTask completed:")
print(history.get_task(task_id))


print("\nRecent tasks:")

for task in history.get_recent_tasks():
    print(task)


    failed_task_id = "task-003"


history.create_task(
    failed_task_id,
    "Read unavailable file"
)

history.update_status(
    failed_task_id,
    "running"
)

history.save_result(
    failed_task_id,
    "File not found"
)

history.update_status(
    failed_task_id,
    "failed"
)


print("\nFailed task:")
print(history.get_task(failed_task_id))