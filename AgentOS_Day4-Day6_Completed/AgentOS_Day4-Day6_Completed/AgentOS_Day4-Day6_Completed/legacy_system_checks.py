
from workload.task import Task
from workload.queue import TaskQueue
from agents.agent import Agent
from agents.manager import AgentManager


def test_priority_queue():
    print("\nTEST 1: Priority Queue")

    queue = TaskQueue()

    low = Task("T1", "compute", 1, "low", {})
    high = Task("T2", "compute", 5, "high", {})
    medium = Task("T3", "compute", 3, "medium", {})

    queue.add_task(low)
    queue.add_task(high)
    queue.add_task(medium)

    first = queue.get_next_task()

    assert first.task_id == "T2", "Highest priority task was not selected!"
    print("PASS: Highest-priority task selected first.")


def test_agent_selection():
    print("\nTEST 2: Capability-Based Agent Selection")

    manager = AgentManager()

    compute_agent = Agent("AGENT-COMPUTE", ["compute"])
    text_agent = Agent("AGENT-TEXT", ["text"])

    manager.register_agent(compute_agent)
    manager.register_agent(text_agent)

    task = Task("T4", "compute", 3, "medium", {})
    selected = manager.find_agent_for_task(task)

    assert selected == compute_agent, "Incorrect agent selected!"
    print("PASS: Task routed to the correct specialized agent.")


def test_load_aware_selection():
    print("\nTEST 3: Load-Aware Selection")

    manager = AgentManager()

    agent1 = Agent("AGENT-1", ["compute"])
    agent2 = Agent("AGENT-2", ["compute"])

    manager.register_agent(agent1)
    manager.register_agent(agent2)

    agent1.completed_tasks = 5
    agent2.completed_tasks = 2

    task = Task("T5", "compute", 3, "medium", {})
    selected = manager.find_agent_for_task(task)

    assert selected == agent2, "Least-loaded agent was not selected!"
    print("PASS: Least-loaded capable agent selected.")


def test_fallback_agent():
    print("\nTEST 4: Fallback Agent")

    manager = AgentManager()

    specialized = Agent("AGENT-COMPUTE", ["compute"])
    fallback = Agent("AGENT-FALLBACK", [])

    manager.register_agent(specialized)
    manager.register_agent(fallback, fallback=True)

    task = Task("T6", "delay", 3, "medium", {})
    selected = manager.find_agent_for_task(task)

    if selected is None:
        selected = manager.get_fallback_agent()

    assert selected == fallback, "Fallback agent was not selected!"
    print("PASS: Unsupported task routed to fallback agent.")


if __name__ == "__main__":
    tests = [
        test_priority_queue,
        test_agent_selection,
        test_load_aware_selection,
        test_fallback_agent,
    ]

    passed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as error:
            print(f"FAIL: {error}")

    print("\n" + "=" * 45)
    print(f"TEST RESULTS: {passed}/{len(tests)} PASSED")
    print("=" * 45)

    if passed == len(tests):
        print("All system tests passed!")
    else:
        print("Some tests failed. Fix them before proceeding.")