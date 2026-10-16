"""Frozen cross-component contracts for AgentOS."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"


class AgentType(str, Enum):
    GENERAL = "general"
    FILE = "file"
    SECURITY = "security"
    MONITORING = "monitoring"
    PLANNING = "planning"
    IMAGE = "image"


class Task(BaseModel):
    id: str
    prompt: str
    agent_type: AgentType = AgentType.GENERAL
    priority: int = Field(default=5, ge=1, le=10)
    estimated_tokens: int = Field(default=256, ge=1)
    complexity: int = Field(default=1, ge=1, le=5)
    risk_level: int = Field(default=1, ge=1, le=5)
    deadline_s: float | None = Field(default=None, gt=0)
    required_capabilities: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.QUEUED
    scheduler: str | None = None
    batch_id: str | None = None
    image_url: str | None = None
    submitted_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    agent: str | None = None
    model: str | None = None
    response: str = ""
    tokens_used: int = 0
    llm_latency_seconds: float = 0.0
    llm_backend: str = "unknown"
    latency_seconds: float | None = None
    scheduler: str | None = None
    batch_id: str | None = None
    image_url: str | None = None
    error: str | None = None


class Policy(BaseModel):
    name: str = "default"
    allowed_tools: list[str] = Field(default_factory=list)
    max_tokens: int | None = Field(default=None, ge=1)
    max_risk_level: int = Field(default=1, ge=1, le=5)


class MetricEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    task_id: str
    event: str
    value: float | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
