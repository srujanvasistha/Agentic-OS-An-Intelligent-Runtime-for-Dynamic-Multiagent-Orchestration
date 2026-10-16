from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class Task:

    task_id: str
    task_type: str
    priority: int
    complexity: str
    payload: Dict[str, Any]

    estimated_duration: float = 0.0

    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    queued_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    status: str = "PENDING"

    # -----------------------------------------
    # Lifecycle methods
    # -----------------------------------------

    def mark_queued(self):

        self.status = "QUEUED"
        self.queued_at = datetime.now().isoformat()

    def mark_running(self):

        self.status = "RUNNING"
        self.started_at = datetime.now().isoformat()

    def mark_completed(self):

        self.status = "COMPLETED"
        self.completed_at = datetime.now().isoformat()

    def mark_failed(self):

        self.status = "FAILED"
        self.completed_at = datetime.now().isoformat()

    # -----------------------------------------
    # Waiting time
    # -----------------------------------------

    def get_waiting_time(self):

        if self.queued_at and self.started_at:

            queued = datetime.fromisoformat(
                self.queued_at
            )

            started = datetime.fromisoformat(
                self.started_at
            )

            return (
                started - queued
            ).total_seconds()

        return 0.0

    # -----------------------------------------
    # Execution time
    # -----------------------------------------

    def get_execution_time(self):

        if self.started_at and self.completed_at:

            started = datetime.fromisoformat(
                self.started_at
            )

            completed = datetime.fromisoformat(
                self.completed_at
            )

            return (
                completed - started
            ).total_seconds()

        return 0.0

    # -----------------------------------------
    # Turnaround time
    # -----------------------------------------

    def get_turnaround_time(self):

        if self.created_at and self.completed_at:

            created = datetime.fromisoformat(
                self.created_at
            )

            completed = datetime.fromisoformat(
                self.completed_at
            )

            return (
                completed - created
            ).total_seconds()

        return 0.0