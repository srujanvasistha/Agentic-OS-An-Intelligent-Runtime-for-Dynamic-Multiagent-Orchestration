import json
import re
from pathlib import Path
from .base_agent import BaseAgent
from tools.filesystem import FileSystemTool
from tools.registry import ToolRegistry


class FileAgent(BaseAgent):
    def __init__(self, tool_registry=None, model: str = "qwen2.5:1.5b", llm_client=None):
        super().__init__(
            name="FileAgent",
            model=model,
            capabilities=[
                "file_listing",
                "file_search",
                "file_reading",
                "file_analysis",
                "file_creation",
                "file_writing",
            ],
            allowed_tools=["filesystem"],
            llm_client=llm_client,
        )
        self.workspace = Path(__file__).resolve().parents[2]
        if tool_registry is not None:
            self.tools = tool_registry
        else:
            self.tools = ToolRegistry()
            self.tools.register("filesystem", FileSystemTool(self.workspace))
        self.filesystem = self.tools.get("filesystem")

    def _parse_file_creation(self, prompt: str) -> tuple[str, str] | None:
        p = prompt.strip()

        # Pattern 1: create [a] file named/called/at <path> with content: <content>
        m = re.search(
            r"(?:create|write|make|save)\s+(?:a\s+|the\s+)?file\s+(?:named\s+|called\s+|at\s+)?['\"]?([^\s'\"\\:]+(?:\.[a-zA-Z0-9]+)?)['\"]?\s+(?:with\s+content|containing|with)[:\s]+(.*)",
            p,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # Pattern 2: create [a] file <path> with content <content>
        m = re.search(
            r"(?:create|write|make|save)\s+(?:a\s+|the\s+)?file\s+['\"]?([^\s'\"\\:]+)['\"]?\s+(?:with\s+content|containing)[:\s]+(.*)",
            p,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # Pattern 3: create/write <path> with content: <content>
        m = re.search(
            r"(?:create|write|save)\s+['\"]?([^\s'\"\\:]+\.[a-zA-Z0-9]+)['\"]?\s+(?:with\s+content|containing)[:\s]+(.*)",
            p,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # Pattern 4: create [a] file <path>: <content>
        m = re.search(
            r"(?:create|write)\s+(?:a\s+)?file\s+['\"]?([^\s'\"\\:]+)['\"]?:\s*(.*)",
            p,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # LLM-based extraction fallback for conversational prompts
        if any(w in p.lower() for w in ["create a file", "create file", "write a file", "save a file", "write to file"]):
            extract_prompt = (
                "Extract the target file path and content from this user instruction.\n"
                f"Instruction: {p}\n"
                "Respond ONLY with a JSON object in this format:\n"
                '{"path": "<filename or path>", "content": "<text to write>"}\n'
                "If no path is specified, use the filename only."
            )
            try:
                raw_json = self.generate(extract_prompt).text
                raw_json = re.sub(r"^```json\s*|\s*```$", "", raw_json.strip())
                data = json.loads(raw_json)
                if isinstance(data, dict) and "path" in data and "content" in data:
                    return str(data["path"]).strip(), str(data["content"]).strip()
            except Exception:
                pass

        return None

    def run(self, prompt: str) -> str:
        prompt_lower = prompt.lower().strip()

        # Check for file creation requests first
        creation = self._parse_file_creation(prompt)
        if creation:
            target_path, content = creation
            return self.filesystem.write_file(target_path, content)

        list_keywords = [
            "list files", "list the files", "show files", "show the files",
            "what files", "which files", "files available", "files in the workspace",
            "workspace files", "directory listing", "list folders", "show folders",
        ]
        if any(keyword in prompt_lower for keyword in list_keywords):
            return self.filesystem.list_files()

        if prompt_lower.startswith("find "):
            target = prompt[5:].strip()
            extensions = {
                "python files": ".py", "markdown files": ".md", "json files": ".json",
                "javascript files": ".js", "css files": ".css",
            }
            for phrase, extension in extensions.items():
                if phrase in target.lower():
                    return self.filesystem.find_by_extension(extension)
            return self.filesystem.find_files(target)

        for prefix in [
            "search for ", "search ", "find files containing ",
            "find files that contain ", "search files for ",
        ]:
            if prompt_lower.startswith(prefix):
                return self.filesystem.search_contents(prompt[len(prefix):].strip())

        if prompt_lower.startswith("read "):
            relative_path = prompt[5:].strip()
            content = self.filesystem.read_file(relative_path)
            if any(content.startswith(prefix) for prefix in (
                "File not found", "Error:", "Not a file", "Could not read"
            )):
                return content
            analysis_prompt = (
                "You are the AgentOS File Analysis Agent.\n\n"
                f"File: {relative_path}\nContents:\n----------------\n{content}\n----------------\n\n"
                f"User request:\n{prompt}\n\nAnalyze only the provided file contents."
            )
            return self.generate(analysis_prompt).text

        workspace_listing = self.filesystem.list_files()
        lines = workspace_listing.splitlines()
        if len(lines) > 40:
            compact_listing = "\n".join(lines[:40]) + f"\n... [and {len(lines) - 40} additional entries in workspace]"
        else:
            compact_listing = workspace_listing

        analysis_prompt = (
            "You are the AgentOS File Analysis Agent.\n\n"
            f"REAL AgentOS workspace listing snippet:\n{compact_listing}\n\n"
            f"User request:\n{prompt}\n\nUse only the workspace information provided. Be concise."
        )
        try:
            res = self.generate(analysis_prompt)
            if res and res.text.strip():
                return res.text
        except Exception:
            pass
        return f"### Workspace Inspection Summary\n\n```\n{compact_listing}\n```"
