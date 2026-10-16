"""Semantic Search & Intent Engine for AgentOS.

Understands user prompts conceptually rather than by literal keywords.
Supports:
1. Semantic intent classification & capability routing for AgentOS agents.
2. Semantic similarity search across workspace files & codebases.
3. Semantic search across historical tasks and execution results.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any


class SemanticConceptProfile:
    """Defines rich conceptual clusters for capabilities."""

    CLUSTERS = {
        "security_analysis": [
            "security", "secure", "vulnerability", "vulnerabilities", "attack", "threat",
            "risk", "permission", "permissions", "authentication", "authorization",
            "malware", "intruder", "intrusion", "breach", "compromise", "credentials",
            "privilege", "privileges", "escalation", "secret", "secrets", "leak", "leakage",
            "exploit", "exploits", "cve", "firewall", "token", "tokens", "encryption",
            "unauthorized", "backdoor", "payload", "sandbox", "audit", "compliance",
            "cve", "zero-day", "phishing", "tampering", "hardening", "isolation"
        ],
        "monitoring": [
            "monitor", "monitoring", "cpu", "processor", "processors", "cores", "compute",
            "memory", "ram", "swap", "volatile", "telemetry", "metrics", "anomaly", "anomalies",
            "operational", "report", "health", "check", "status", "queue", "depth",
            "latency", "throughput", "diagnostics", "resource", "usage", "utilization", "load",
            "strain", "saturation", "bottleneck", "bottlenecks", "throttling", "performance",
            "temperature", "uptime", "i/o", "disk", "capacity", "stress", "benchmark", "telemetric"
        ],
        "file_search": [
            "file", "files", "folder", "folders", "directory", "directories", "workspace",
            "read", "find", "search", "list", "python", "markdown", "json", "yaml", "config",
            "configuration", "create", "write", "save", "document", "documents", "store",
            "storage", "repository", "archive", "contents", "catalog", "path", "paths",
            "source", "tree", "blueprint", "inspect", "locate", "tarball", "filesystem"
        ],
        "task_planning": [
            "plan", "planning", "subtask", "subtasks", "break down", "decompose", "decomposition",
            "dependency", "dependencies", "assign", "orchestrate", "orchestration", "workflow",
            "pipeline", "multi-step", "combine", "output", "roadmap", "milestone", "milestones",
            "schedule", "phases", "stages", "sequential", "parallel", "strategy", "coordination",
            "graph", "dag", "dispatch", "divide", "tasks", "work"
        ],
        "general_questions": [
            "explain", "what", "how", "why", "who", "tell", "describe", "overview", "concept",
            "concepts", "tutorial", "guide", "difference", "compare", "summary", "summarize",
            "help", "assistant", "objectives", "purpose", "fundamentals", "theory", "kernel",
            "definition", "meaning", "principles"
        ]
    }


class SemanticVectorizer:
    """TF-IDF and conceptual semantic vector space model."""

    # Words with no semantic intent value
    STOP_WORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any",
        "are", "aren't", "as", "at", "be", "because", "been", "before", "being", "below",
        "between", "both", "but", "by", "can", "can't", "cannot", "could", "couldn't", "did",
        "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few",
        "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
        "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him",
        "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into",
        "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't",
        "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
        "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
        "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that",
        "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's",
        "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through",
        "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll",
        "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
        "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
        "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
        "yourself", "yourselves"
    }

    @classmethod
    def tokenize(cls, text: str) -> list[str]:
        """Extracts normalized semantic tokens from text."""
        words = re.findall(r"[a-zA-Z0-9_\-\.\/]+", text.lower())
        tokens = []
        for w in words:
            # Strip outer punctuation
            w_clean = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", w)
            if len(w_clean) >= 2 and w_clean not in cls.STOP_WORDS:
                tokens.append(w_clean)
        return tokens

    CONCEPT_EXPANSIONS = {
        # Hardware / Monitoring concepts
        "processor": ["cpu", "compute", "hardware"],
        "processors": ["cpu", "compute", "hardware"],
        "cores": ["cpu", "processor", "compute"],
        "strain": ["load", "saturation", "stress", "monitoring"],
        "diagnostics": ["metrics", "monitoring", "telemetry", "health"],
        "thermal": ["temperature", "throttling", "hardware", "monitoring"],
        "throttling": ["bottleneck", "hardware", "performance"],
        "volatile": ["memory", "ram", "cache"],
        "saturation": ["load", "memory", "cpu", "strain"],
        "bottlenecks": ["bottleneck", "performance", "latency"],
        # Security concepts
        "intruder": ["attacker", "threat", "security", "unauthorized"],
        "intruders": ["attacker", "threat", "security", "unauthorized"],
        "breach": ["vulnerability", "attack", "compromise", "security"],
        "compromise": ["breach", "vulnerability", "threat", "security"],
        "escalate": ["privilege", "authorization", "permission", "security"],
        "escalated": ["privilege", "authorization", "permission", "security"],
        "standing": ["privilege", "permission"],
        "credentials": ["secret", "token", "authentication", "password"],
        "tokens": ["secret", "credentials", "authentication"],
        "secrets": ["credentials", "token", "password", "security"],
        "exfiltrate": ["leak", "breach", "attack", "security"],
        # Files / Storage concepts
        "blueprint": ["file", "document", "specification"],
        "blueprints": ["files", "documents", "specifications"],
        "store": ["storage", "repository", "directory", "filesystem"],
        "repository": ["storage", "directory", "folder", "workspace"],
        "catalog": ["list", "directory", "files", "inventory"],
        # Planning / Workflow concepts
        "milestone": ["subtask", "stage", "plan", "milestones"],
        "milestones": ["subtasks", "stages", "plan"],
        "roadmap": ["plan", "workflow", "strategy", "timeline"],
        "sequential": ["steps", "pipeline", "dependencies", "phases"],
    }

    @classmethod
    def vectorize(cls, text: str) -> dict[str, float]:
        """Computes sublinear normalized TF vector with semantic concept expansions."""
        tokens = cls.tokenize(text)
        if not tokens:
            return {}
        counts: dict[str, float] = Counter(tokens)
        
        # Apply semantic concept expansion weights
        for t in list(tokens):
            for syn in cls.CONCEPT_EXPANSIONS.get(t, []):
                counts[syn] = counts.get(syn, 0.0) + 0.55

        vec = {word: 1.0 + math.log(1.0 + count) for word, count in counts.items()}
        # Normalize to unit length
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm > 0:
            return {k: v / norm for k, v in vec.items()}
        return vec

    @classmethod
    def cosine_similarity(cls, vec1: dict[str, float], vec2: dict[str, float]) -> float:
        """Calculates cosine similarity between two sparse unit vectors."""
        if not vec1 or not vec2:
            return 0.0
        # Iterate over smaller dict
        if len(vec1) > len(vec2):
            vec1, vec2 = vec2, vec1
        return sum(val * vec2.get(k, 0.0) for k, val in vec1.items())


class SemanticSearchEngine:
    """
    Main Semantic Search & Intent Engine for AgentOS.
    """

    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = workspace_root or Path(__file__).resolve().parents[2]
        self._capability_vectors: dict[str, dict[str, float]] = {}
        self._build_capability_vectors()

    def _build_capability_vectors(self):
        """Constructs semantic capability centroid vectors."""
        for cap, terms in SemanticConceptProfile.CLUSTERS.items():
            text = " ".join(terms)
            self._capability_vectors[cap] = SemanticVectorizer.vectorize(text)

    def classify_intent(self, prompt: str) -> tuple[str, float, dict[str, float]]:
        """
        Classifies user prompt intent semantically rather than by exact keywords.
        Returns:
            (best_capability, confidence_score, all_scores)
        """
        prompt_vec = SemanticVectorizer.vectorize(prompt)
        if not prompt_vec:
            return "general_questions", 0.0, {}

        scores: dict[str, float] = {}
        for cap, cap_vec in self._capability_vectors.items():
            sim = SemanticVectorizer.cosine_similarity(prompt_vec, cap_vec)
            scores[cap] = round(sim, 4)

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_cap, best_score = sorted_scores[0]

        # If highest score is too weak (< 0.05), fallback to general
        if best_score < 0.05:
            return "general_questions", best_score, scores

        return best_cap, best_score, scores

    def search_workspace(
        self, query: str, top_k: int = 5, extensions: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Performs semantic similarity search over workspace files and code snippets.
        """
        query_vec = SemanticVectorizer.vectorize(query)
        if not query_vec:
            return []

        ignored_dirs = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "build", "dist"}
        allowed_exts = set(extensions or [".py", ".jsx", ".js", ".json", ".md", ".txt", ".html", ".css", ".csv"])

        results = []
        try:
            for path in self.workspace_root.rglob("*"):
                if any(part in ignored_dirs for part in path.parts):
                    continue
                if not path.is_file():
                    continue
                if path.suffix.lower() not in allowed_exts:
                    continue

                rel_path = str(path.relative_to(self.workspace_root)).replace("\\", "/")
                # Vectorize filename and path
                path_text = rel_path.replace("/", " ").replace("_", " ").replace(".", " ")

                # Sample up to first 2500 chars of file for content matching
                try:
                    content_snippet = path.read_text(encoding="utf-8", errors="ignore")[:3000]
                except Exception:
                    content_snippet = ""

                doc_text = f"{path_text} {path_text} {content_snippet}"
                doc_vec = SemanticVectorizer.vectorize(doc_text)
                sim = SemanticVectorizer.cosine_similarity(query_vec, doc_vec)

                if sim > 0.02:
                    # Find snippet around most relevant matching word
                    best_snippet = self._extract_relevant_snippet(content_snippet, query)
                    results.append({
                        "path": rel_path,
                        "filename": path.name,
                        "score": round(sim, 4),
                        "snippet": best_snippet,
                        "size_bytes": path.stat().st_size,
                    })
        except Exception:
            pass

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def search_tasks(
        self, query: str, task_records: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Semantically searches through executed task prompts and responses.
        """
        query_vec = SemanticVectorizer.vectorize(query)
        if not query_vec or not task_records:
            return []

        results = []
        for t in task_records:
            prompt_text = str(t.get("prompt") or "")
            resp_text = str(t.get("response") or "")[:500]
            agent_text = str(t.get("agent") or "")
            doc_text = f"{prompt_text} {resp_text} {agent_text}"

            doc_vec = SemanticVectorizer.vectorize(doc_text)
            sim = SemanticVectorizer.cosine_similarity(query_vec, doc_vec)

            if sim > 0.02:
                results.append({
                    "task_id": t.get("task_id") or t.get("id"),
                    "prompt": prompt_text[:120] + ("…" if len(prompt_text) > 120 else ""),
                    "agent": agent_text,
                    "score": round(sim, 4),
                    "status": t.get("status"),
                    "scheduler": t.get("scheduler"),
                    "latency_seconds": t.get("latency_seconds"),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _extract_relevant_snippet(self, content: str, query: str, max_chars: int = 180) -> str:
        """Extracts a readable snippet from content near matching query tokens."""
        if not content:
            return ""
        tokens = SemanticVectorizer.tokenize(query)
        for t in tokens:
            idx = content.lower().find(t.lower())
            if idx != -1:
                start = max(0, idx - 40)
                end = min(len(content), idx + max_chars - 40)
                snip = content[start:end].replace("\n", " ").strip()
                return ("…" if start > 0 else "") + snip + ("…" if end < len(content) else "")
        return content[:max_chars].replace("\n", " ").strip() + "…"


# Global engine singleton
semantic_engine = SemanticSearchEngine()
