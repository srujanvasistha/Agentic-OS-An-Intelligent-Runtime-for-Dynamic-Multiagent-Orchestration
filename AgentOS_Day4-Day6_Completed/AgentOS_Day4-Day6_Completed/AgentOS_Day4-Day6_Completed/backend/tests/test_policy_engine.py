from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from security.policy import PolicyEngine


def test_policy_allows_read_only_fileagent_workspace_read(tmp_path):
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
    engine = PolicyEngine(tmp_path)
    decision = engine.check("FileAgent", "filesystem", {"operation": "read_file", "relative_path": "notes.txt"})
    assert decision.allowed


def test_policy_denies_path_traversal(tmp_path):
    engine = PolicyEngine(tmp_path)
    decision = engine.check("FileAgent", "filesystem", {"operation": "read_file", "relative_path": "../../etc/passwd"})
    assert not decision.allowed
    assert "escapes" in decision.reason.lower()


def test_policy_denies_sensitive_paths(tmp_path):
    engine = PolicyEngine(tmp_path)
    decision = engine.check("FileAgent", "filesystem", {"operation": "read_file", "relative_path": ".env"})
    assert not decision.allowed
    assert "sensitive" in decision.reason.lower()


def test_policy_denies_write_shell_and_network(tmp_path):
    engine = PolicyEngine(tmp_path)
    assert not engine.check("FileAgent", "filesystem", {"operation": "write_file", "relative_path": "x"}).allowed
    assert not engine.check("GeneralAgent", "shell", {"command": "echo unsafe"}).allowed
    assert not engine.check("GeneralAgent", "network", {"url": "https://example.invalid"}).allowed


def test_policy_denies_unknown_agent_and_unknown_tool(tmp_path):
    engine = PolicyEngine(tmp_path)
    assert not engine.check("UnknownAgent", "system_info", {}).allowed
    assert not engine.check("GeneralAgent", "unknown", {}).allowed
