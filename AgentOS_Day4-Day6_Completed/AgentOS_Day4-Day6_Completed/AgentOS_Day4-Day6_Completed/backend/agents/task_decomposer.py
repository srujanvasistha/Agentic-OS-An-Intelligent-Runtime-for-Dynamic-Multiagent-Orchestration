"""Task decomposition and multi-agent job scheduling for AgentOS.

Enables submitting a single composite prompt containing multiple indexed questions
or sub-tasks for one or more agents. Parses, indexes, routes, and creates jobs
for the AgentOS scheduler.
"""

from __future__ import annotations

import re
import uuid
from typing import Any
from schemas import AgentType, Task, TaskStatus


class TaskDecomposer:
    """
    Decomposes single prompts containing multiple indexed questions/sub-tasks,
    resolves agent assignments (via explicit hints or automated classification),
    and creates discrete tasks for AgentOS job scheduling.
    """

    AGENT_NAME_MAP = {
        "general": AgentType.GENERAL,
        "generalagent": AgentType.GENERAL,
        "file": AgentType.FILE,
        "fileagent": AgentType.FILE,
        "security": AgentType.SECURITY,
        "securityagent": AgentType.SECURITY,
        "monitoring": AgentType.MONITORING,
        "monitoringagent": AgentType.MONITORING,
        "planning": AgentType.PLANNING,
        "planningagent": AgentType.PLANNING,
        "image": AgentType.IMAGE,
        "imageagent": AgentType.IMAGE,
    }

    # Matches indexed prefixes: [1], (1), 1., 1), Q1:, Question 1:, Task 1:
    INDEX_PATTERN = re.compile(
        r"(?:^|\n|\s+)(?:\[(\d+)\]|\((\d+)\)|(\d+)[\.\)]|Q(\d+)[:\.\-\s]|Question\s+(\d+)[:\.\-\s]|Task\s+(\d+)[:\.\-\s])\s*",
        re.IGNORECASE,
    )

    # Matches explicit agent hints: (FileAgent), [MonitoringAgent], SecurityAgent:, agent: File
    AGENT_HINT_PATTERNS = [
        re.compile(r"^\s*\[([a-zA-Z]+)\]\s*"),
        re.compile(r"^\s*\(([a-zA-Z]+)\)\s*"),
        re.compile(r"^\s*@([a-zA-Z]+)\s*"),
        re.compile(r"^\s*([a-zA-Z]+Agent)\s*[:\-\s]\s*", re.IGNORECASE),
        re.compile(r"^\s*agent\s*[:\=]\s*([a-zA-Z]+)\s*[:\-\s]*", re.IGNORECASE),
    ]

    PRIORITY_PATTERN = re.compile(
        r"\[(?:p|priority)\s*[:=\s]?\s*(\d+)\]|\((?:p|priority)\s*[:=\s]?\s*(\d+)\)|\b(?:priority|prio)\s*[:=]\s*(\d+)\b",
        re.IGNORECASE,
    )
    TOKEN_PATTERN = re.compile(
        r"\[(?:tokens?)\s*[:=\s]?\s*(\d+)\]|\((?:tokens?)\s*[:=\s]?\s*(\d+)\)",
        re.IGNORECASE,
    )

    @classmethod
    def _extract_priority(cls, text: str) -> tuple[int | None, str]:
        match = cls.PRIORITY_PATTERN.search(text)
        if match:
            raw_val = next(g for g in match.groups() if g is not None)
            val = max(1, min(10, int(raw_val)))
            clean = cls.PRIORITY_PATTERN.sub("", text, count=1).strip()
            return val, clean
        return None, text

    @classmethod
    def _extract_tokens(cls, text: str) -> tuple[int | None, str]:
        match = cls.TOKEN_PATTERN.search(text)
        if match:
            raw_val = next(g for g in match.groups() if g is not None)
            val = max(16, min(8192, int(raw_val)))
            clean = cls.TOKEN_PATTERN.sub("", text, count=1).strip()
            return val, clean
        return None, text

    @classmethod
    def is_composite(cls, prompt: str) -> bool:
        """Determines if a prompt contains multiple indexed questions/sub-tasks."""
        if not prompt or len(prompt.strip()) < 5:
            return False
        matches = list(cls.INDEX_PATTERN.finditer(prompt))
        return len(matches) >= 2

    @classmethod
    def decompose(
        cls,
        prompt: str,
        task_router: Any = None,
        default_agent_type: AgentType | None = None,
    ) -> list[dict[str, Any]]:
        """
        Decomposes a prompt into indexed sub-questions with agent mapping.
        If the prompt is not composite, returns a single-item list.
        """
        prompt = prompt.strip()
        matches = list(cls.INDEX_PATTERN.finditer(prompt))

        if len(matches) < 2:
            # Single task
            prio, text_no_prio = cls._extract_priority(prompt)
            tokens, text_no_tok = cls._extract_tokens(text_no_prio)
            agent_type, clean_prompt = cls._extract_explicit_agent(text_no_tok)
            if prio is None:
                prio, clean_prompt = cls._extract_priority(clean_prompt)
            if agent_type is None:
                agent_type = default_agent_type or (
                    cls._classify_agent(clean_prompt, task_router) if task_router else AgentType.GENERAL
                )
            return [
                {
                    "index": 1,
                    "prompt": clean_prompt,
                    "raw_text": prompt,
                    "agent_type": agent_type,
                    "agent_name": cls._agent_type_to_name(agent_type),
                    "explicit_agent": bool(agent_type != default_agent_type),
                    "priority": prio,
                    "estimated_tokens": tokens,
                }
            ]

        subtasks: list[dict[str, Any]] = []
        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(prompt)
            raw_text = prompt[start:end].strip()

            # Extract index number from the matched groups
            idx_str = next((g for g in match.groups() if g is not None), str(i + 1))
            try:
                index_num = int(idx_str)
            except ValueError:
                index_num = i + 1

            # Extract priority and tokens first if present
            prio, text_step1 = cls._extract_priority(raw_text)
            tokens, text_step2 = cls._extract_tokens(text_step1)
            agent_type, clean_prompt = cls._extract_explicit_agent(text_step2)
            if prio is None:
                prio, clean_prompt = cls._extract_priority(clean_prompt)
            if tokens is None:
                tokens, clean_prompt = cls._extract_tokens(clean_prompt)

            # If no explicit agent tag, route automatically or use default
            if agent_type is None:
                if default_agent_type is not None:
                    agent_type = default_agent_type
                elif task_router is not None:
                    agent_type = cls._classify_agent(clean_prompt, task_router)
                else:
                    agent_type = AgentType.GENERAL

            subtasks.append(
                {
                    "index": index_num,
                    "prompt": clean_prompt,
                    "raw_text": raw_text,
                    "agent_type": agent_type,
                    "agent_name": cls._agent_type_to_name(agent_type),
                    "explicit_agent": bool(agent_type != default_agent_type),
                    "priority": prio,
                    "estimated_tokens": tokens,
                }
            )

        return subtasks

    @classmethod
    def _extract_explicit_agent(cls, text: str) -> tuple[AgentType | None, str]:
        """Checks for explicit agent mentions in the question text and strips the tag."""
        for pattern in cls.AGENT_HINT_PATTERNS:
            match = pattern.match(text)
            if match:
                tag = match.group(1).strip().lower()
                if tag in cls.AGENT_NAME_MAP:
                    agent_type = cls.AGENT_NAME_MAP[tag]
                    clean_text = text[match.end():].strip()
                    return agent_type, clean_text
        return None, text

    @classmethod
    def _classify_agent(cls, text: str, task_router: Any) -> AgentType:
        """Uses TaskRouter to determine the best agent type for a sub-question."""
        try:
            capability = task_router.classify(text)
            cap_map = {
                "file_search": AgentType.FILE,
                "file_listing": AgentType.FILE,
                "file_reading": AgentType.FILE,
                "file_creation": AgentType.FILE,
                "monitoring": AgentType.MONITORING,
                "system_metrics": AgentType.MONITORING,
                "security_analysis": AgentType.SECURITY,
                "risk_analysis": AgentType.SECURITY,
                "task_planning": AgentType.PLANNING,
                "subtask_decomposition": AgentType.PLANNING,
                "general_questions": AgentType.GENERAL,
                "image_generation": AgentType.IMAGE,
                "image_analysis": AgentType.IMAGE,
            }
            return cap_map.get(capability, AgentType.GENERAL)
        except Exception:
            return AgentType.GENERAL

    @classmethod
    def _agent_type_to_name(cls, agent_type: AgentType) -> str:
        names = {
            AgentType.GENERAL: "GeneralAgent",
            AgentType.FILE: "FileAgent",
            AgentType.SECURITY: "SecurityAgent",
            AgentType.MONITORING: "MonitoringAgent",
            AgentType.PLANNING: "PlanningAgent",
            AgentType.IMAGE: "ImageAgent",
        }
        return names.get(agent_type, "GeneralAgent")

    @classmethod
    def create_scheduled_tasks(
        cls,
        subtasks: list[dict[str, Any]],
        priority: int = 5,
        estimated_tokens: int = 256,
        complexity: int = 1,
        risk_level: int = 1,
        deadline_s: float | None = None,
        batch_id: str | None = None,
    ) -> list[Task]:
        """Creates Task domain objects ready to be enqueued into the AgentOS scheduler."""
        batch = batch_id or str(uuid.uuid4())
        total = len(subtasks)
        tasks = []

        for sub in subtasks:
            task_id = str(uuid.uuid4())
            # Format prompt with index notation for scheduler logging
            indexed_prompt = f"[{sub['index']}/{total}] {sub['prompt']}" if total > 1 else sub['prompt']
            task = Task(
                id=task_id,
                prompt=indexed_prompt,
                agent_type=sub["agent_type"],
                priority=priority,
                estimated_tokens=estimated_tokens,
                complexity=complexity,
                risk_level=risk_level,
                deadline_s=deadline_s,
                required_capabilities=[],
                status=TaskStatus.QUEUED,
            )
            tasks.append(task)

        return tasks
