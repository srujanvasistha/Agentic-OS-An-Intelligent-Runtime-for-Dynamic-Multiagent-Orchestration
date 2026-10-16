import sys
import os

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.append(PROJECT_ROOT)

import streamlit as st

from workload.generator import generate_workload
from workload.queue import TaskQueue
from agents.agent import Agent
from agents.manager import AgentManager
from scheduler.scheduler import Scheduler


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="AgenticOS Monitor",
    page_icon="🤖",
    layout="wide"
)


# =========================================================
# TITLE
# =========================================================

st.title("🤖 AgenticOS Runtime Monitor")

st.write(
    "Intelligent Runtime for Dynamic Multiagent Orchestration"
)

st.divider()


# =========================================================
# CREATE AGENT MANAGER
# =========================================================

manager = AgentManager()

agent1 = Agent(
    "AGENT-001",
    ["compute", "data"]
)

agent2 = Agent(
    "AGENT-002",
    ["network", "io"]
)

agent3 = Agent(
    "AGENT-003",
    ["ml", "text"]
)

fallback = Agent(
    "AGENT-FALLBACK",
    []
)


manager.register_agent(agent1)
manager.register_agent(agent2)
manager.register_agent(agent3)

manager.register_agent(
    fallback,
    fallback=True
)


# =========================================================
# CREATE SCHEDULER
# =========================================================

scheduler = Scheduler(manager)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Runtime Controls")

num_tasks = st.sidebar.slider(
    "Number of Tasks",
    min_value=5,
    max_value=40,
    value=10
)

seed = st.sidebar.number_input(
    "Workload Seed",
    min_value=1,
    max_value=1000,
    value=42
)

run_button = st.sidebar.button(
    "▶ Run Workload"
)


# =========================================================
# RUN WORKLOAD
# =========================================================

if run_button:

    workload = generate_workload(
        num_tasks=num_tasks,
        seed=seed
    )

    scheduler.submit_tasks(workload)

    scheduler.run()

    st.session_state["scheduler"] = scheduler
    st.session_state["manager"] = manager


# =========================================================
# DISPLAY RESULTS
# =========================================================

if "scheduler" in st.session_state:

    scheduler = st.session_state["scheduler"]
    manager = st.session_state["manager"]

    statistics = scheduler.get_statistics()

    metrics = scheduler.metrics.get_report()

    # -----------------------------------------------------
    # TASK METRICS
    # -----------------------------------------------------

    st.subheader("📊 Task Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Tasks",
        statistics["total_tasks"]
    )

    col2.metric(
        "Completed",
        statistics["completed_tasks"]
    )

    col3.metric(
        "Failed",
        statistics["failed_tasks"]
    )

    col4.metric(
        "Fallback Tasks",
        statistics["fallback_tasks"]
    )

    st.divider()

    # -----------------------------------------------------
    # EXECUTION METRICS
    # -----------------------------------------------------

    st.subheader("⚡ Execution Metrics")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Runtime",
        f"{metrics['total_runtime']} s"
    )

    col2.metric(
        "Avg Waiting Time",
        f"{metrics['average_waiting_time']} s"
    )

    col3.metric(
        "Avg Execution Time",
        f"{metrics['average_execution_time']} s"
    )

    col4.metric(
        "Throughput",
        f"{metrics['throughput']} tasks/s"
    )

    st.divider()

    # -----------------------------------------------------
    # AGENT STATUS
    # -----------------------------------------------------

    st.subheader("🤖 Agent Status")

    agent_stats = manager.get_statistics()

    for agent in agent_stats:

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.write(
            f"**{agent['agent_id']}**"
        )

        col2.write(
            f"Status: {agent['status']}"
        )

        col3.write(
            f"Load: {agent['load']}"
        )

        col4.write(
            f"Success: {agent['success_rate']}%"
        )

        col5.write(
            f"Score: {agent['performance_score']}"
        )

    st.divider()

    # -----------------------------------------------------
    # PERFORMANCE TABLE
    # -----------------------------------------------------

    st.subheader("📈 Agent Performance")

    st.dataframe(
        agent_stats,
        use_container_width=True
    )

else:

    st.info(
        "Configure the workload from the sidebar "
        "and click **Run Workload**."
    )