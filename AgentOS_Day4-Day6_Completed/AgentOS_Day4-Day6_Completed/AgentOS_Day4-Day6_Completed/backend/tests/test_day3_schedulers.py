from datetime import datetime, timedelta

from schemas import AgentType, Task
from scheduler.fifo import FIFOScheduler
from scheduler.round_robin import RoundRobinScheduler
from scheduler.priority import PriorityScheduler
from scheduler.resource_aware import ResourceAwareScheduler


def make_task(task_id, agent=AgentType.GENERAL, priority=5,
              complexity=1, tokens=100, risk=1, deadline=None):
    return Task(
        id=task_id,
        prompt=f"Task {task_id}",
        agent_type=agent,
        priority=priority,
        complexity=complexity,
        estimated_tokens=tokens,
        risk_level=risk,
        deadline_s=deadline,
    )


def test_fifo_preserves_order():
    scheduler = FIFOScheduler()
    tasks = [make_task("a"), make_task("b")]
    for task in tasks:
        scheduler.enqueue(task)

    assert scheduler.next_task().id == "a"
    assert scheduler.next_task().id == "b"
    assert scheduler.next_task() is None


def test_round_robin_interleaves_agents():
    scheduler = RoundRobinScheduler()
    scheduler.enqueue(make_task("g1", AgentType.GENERAL))
    scheduler.enqueue(make_task("g2", AgentType.GENERAL))
    scheduler.enqueue(make_task("f1", AgentType.FILE))
    scheduler.enqueue(make_task("s1", AgentType.SECURITY))

    assert [scheduler.next_task().id for _ in range(4)] == [
        "g1", "f1", "s1", "g2"
    ]
    assert not scheduler.has_tasks()


def test_priority_highest_first_and_stable_ties():
    scheduler = PriorityScheduler()
    scheduler.enqueue(make_task("low", priority=2))
    scheduler.enqueue(make_task("high1", priority=9))
    scheduler.enqueue(make_task("high2", priority=9))

    assert [scheduler.next_task().id for _ in range(3)] == [
        "high1", "high2", "low"
    ]


def test_resource_scheduler_prefers_higher_priority():
    scheduler = ResourceAwareScheduler()
    scheduler.enqueue(make_task("low", priority=1))
    scheduler.enqueue(make_task("high", priority=10))

    assert scheduler.next_task().id == "high"


def test_resource_pressure_penalizes_complex_high_risk_task():
    scheduler = ResourceAwareScheduler()
    now = datetime.now()
    heavy = make_task(
        "heavy", priority=5, complexity=5, tokens=1000, risk=5
    )
    light = make_task(
        "light", priority=5, complexity=1, tokens=10, risk=1
    )

    assert scheduler.score(light, {"cpu_percent": 95}, now) > (
        scheduler.score(heavy, {"cpu_percent": 95}, now)
    )


def test_resource_scheduler_empty_and_clear():
    scheduler = ResourceAwareScheduler()
    assert scheduler.next_task() is None

    scheduler.enqueue(make_task("a"))
    scheduler.clear()

    assert scheduler.size() == 0
    assert not scheduler.has_tasks()
    assert scheduler.next_task() is None


def test_task_decomposer_extracts_inline_priority_and_tokens():
    from agents.task_decomposer import TaskDecomposer
    prompt = """
    [1] [P1] (GeneralAgent) Low priority analysis
    [2] (SecurityAgent) [P10] Critical security scan
    [3] [Priority 6] (MonitoringAgent) [tokens: 500] Telemetry diagnostics
    """
    subtasks = TaskDecomposer.decompose(prompt)
    assert len(subtasks) == 3
    assert subtasks[0]["priority"] == 1
    assert subtasks[1]["priority"] == 10
    assert subtasks[2]["priority"] == 6
    assert subtasks[2]["estimated_tokens"] == 500


def test_priority_scheduler_reorders_decomposed_subtasks():
    from agents.task_decomposer import TaskDecomposer
    prompt = """
    [1] [P1] (GeneralAgent) Low priority analysis
    [2] [P10] (SecurityAgent) Critical security scan
    [3] [P6] (MonitoringAgent) Telemetry diagnostics
    """
    subtasks = TaskDecomposer.decompose(prompt)
    scheduler = PriorityScheduler()
    for sub in subtasks:
        scheduler.enqueue(make_task(str(sub["index"]), priority=sub["priority"]))

    order = [scheduler.next_task().id for _ in range(3)]
    assert order == ["2", "3", "1"]  # P10, then P6, then P1

