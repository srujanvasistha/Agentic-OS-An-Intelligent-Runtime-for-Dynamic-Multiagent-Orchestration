from .base_agent import BaseAgent
from tools.filesystem import FileSystemTool
from tools.registry import ToolRegistry
from pathlib import Path


class FileAgent(BaseAgent):
    def __init__(self, tool_registry=None, model: str = "qwen2.5:1.5b", llm_client=None):
        super().__init__(
            name="FileAgent",
            model=model,
            capabilities=["file_listing", "file_search", "file_reading", "file_analysis"],
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

    def run(self, prompt: str) -> str:
        prompt_lower = prompt.lower().strip()

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
        analysis_prompt = (
            "You are the AgentOS File Analysis Agent.\n\n"
            f"REAL AgentOS workspace listing:\n{workspace_listing}\n\n"
            f"User request:\n{prompt}\n\nUse only the workspace information provided."
        )
        return self.generate(analysis_prompt).text
