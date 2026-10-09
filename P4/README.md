# AgentOS - P4 Memory Module

## Purpose

This project implements the persistent memory subsystem
for AgentOS.

## Features

- SQLite persistent storage
- Save memory
- Retrieve memory
- Update memory
- Delete memory
- Recent memory retrieval
- Persistent storage across program restarts

## Technology

- Python
- SQLite
- pytest

## Run Demo

```bash
python demo/day1_memory_demo.py

## P4 Project Components

### Day 1: Persistent SQLite Memory
- Stores key-value memories.
- Supports retrieving, deleting, and listing memories.
- Persists data across program runs.

### Day 2: Task History
- Creates and tracks tasks.
- Records task status, results, and timestamps.
- Supports retrieving individual and recent tasks.

### Day 3: System Resource Monitor
- Collects CPU usage.
- Collects RAM usage and availability.
- Collects disk usage.
- Reports CPU core count and running process count.

### Day 4: Metrics Logger
- Records task ID, agent name, status, and duration.
- Records CPU and RAM usage.
- Supports token-count metrics when available.
- Exports metrics to CSV and reads exported records.

### Day 5: Standalone Integration Demo
- Demonstrates the P4 components working together.
- Creates and updates a task.
- Collects a system resource snapshot.
- Stores the result in task history and persistent memory.
- Logs task metrics and exports a CSV file.

## Running the Project

Activate the virtual environment:

```powershell
cd D:\Agentos-P4
.\.venv\Scripts\Activate.ps1
```

Run the integration demo:

```powershell
python -m demo.day5_integration_demo
```

Run all tests:

```powershell
python -m pytest -v
```

## Output Files

- `data/agentos_memory.db`: SQLite database for memory and task history.
- `data/metrics/metrics.csv`: Exported metrics from the latest demo run.

## Project Scope

This is a standalone P4 implementation developed independently of P1's files and services. Integration with the wider AgentOS project can be performed later through agreed interfaces.
