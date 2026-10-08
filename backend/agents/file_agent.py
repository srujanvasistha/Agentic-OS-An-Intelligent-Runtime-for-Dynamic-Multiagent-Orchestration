from .base_agent import BaseAgent
from tools.registry import ToolRegistry


class FileAgent(BaseAgent):
    def __init__(self, tool_registry=None, model: str = "qwen2.5:1.5b", llm_client=None):
        super().__init__(
            name="FileAgent",
            model=model,
            capabilities=["file_listing", "file_search", "file_reading", "file_analysis"],
            allowed_tools=["filesystem"],
            llm_client=llm_client,
        )
        self.tools = tool_registry if tool_registry is not None else ToolRegistry()

    def run(self, prompt: str) -> str:
        prompt_lower = prompt.lower().strip()

        list_keywords = [
            "list files", "list the files", "show files", "show the files",
            "what files", "which files", "files available", "files in the workspace",
            "workspace files", "directory listing", "list folders", "show folders",
        ]
        if any(keyword in prompt_lower for keyword in list_keywords):
            return self.call_tool("filesystem", {"operation": "list_files"})

        if prompt_lower.startswith("find "):
            target = prompt[5:].strip()
            extensions = {
                "python files": ".py", "markdown files": ".md", "json files": ".json",
                "javascript files": ".js", "css files": ".css",
            }
            for phrase, extension in extensions.items():
                if phrase in target.lower():
                    return self.call_tool("filesystem", {"operation": "find_by_extension", "extension": extension})
            return self.call_tool("filesystem", {"operation": "find_files", "filename": target})

        for prefix in [
            "search for ", "search ", "find files containing ",
            "find files that contain ", "search files for ",
        ]:
            if prompt_lower.startswith(prefix):
                return self.call_tool("filesystem", {"operation": "search_contents", "search_text": prompt[len(prefix):].strip()})

        if prompt_lower.startswith("read "):
            relative_path = prompt[5:].strip()
            source = "logs" if relative_path.lower().endswith(".log") else "file_contents"
            content = self.call_tool("filesystem", {"operation": "read_file", "relative_path": relative_path}, source=source)
            if content.startswith("[UNTRUSTED_CONTENT ") and any(error in content for error in (
                "File not found", "Error:", "Not a file", "Could not read"
            )):
                return content
            analysis_prompt = (
                "You are the AgentOS File Analysis Agent.\n\n"
                f"File: {relative_path}\nContents:\n----------------\n{content}\n----------------\n\n"
                f"User request:\n{prompt}\n\nAnalyze only the provided file contents."
            )
            return self.generate(analysis_prompt).text

        workspace_listing = self.call_tool("filesystem", {"operation": "list_files"})
        analysis_prompt = (
            "You are the AgentOS File Analysis Agent.\n\n"
            f"REAL AgentOS workspace listing:\n{workspace_listing}\n\n"
            f"User request:\n{prompt}\n\nUse only the workspace information provided."
        )
        return self.generate(analysis_prompt).text
