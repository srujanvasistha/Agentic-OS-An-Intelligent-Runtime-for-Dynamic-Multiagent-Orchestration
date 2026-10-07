from pathlib import Path


class FileSystemTool:
    """
    Safe filesystem access restricted to the AgentOS workspace.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

        self.ignored_dirs = {
            ".git",
            ".venv",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
        }

    def _is_ignored(self, path: Path) -> bool:
        try:
            relative = path.relative_to(self.workspace)

            return any(
                part in self.ignored_dirs
                for part in relative.parts
            )

        except ValueError:
            return True

    def list_files(self) -> str:
        lines = [
            f"Workspace: {self.workspace}",
            ""
        ]

        try:
            for path in sorted(self.workspace.rglob("*")):

                if self._is_ignored(path):
                    continue

                try:
                    relative = path.relative_to(self.workspace)

                    if path.is_dir():
                        lines.append(f"[DIR]  {relative}")

                    elif path.is_file():
                        lines.append(f"[FILE] {relative}")

                except (OSError, PermissionError):
                    continue

        except (OSError, PermissionError) as exc:
            return f"Could not list workspace: {exc}"

        return "\n".join(lines)

    def find_files(self, filename: str) -> str:
        filename = filename.strip().lower()

        if not filename:
            return "Please provide a filename."

        matches = []

        try:
            for path in self.workspace.rglob("*"):

                if self._is_ignored(path):
                    continue

                if not path.is_file():
                    continue

                if path.name.lower() == filename:
                    matches.append(
                        str(path.relative_to(self.workspace))
                    )

        except (OSError, PermissionError) as exc:
            return f"Search failed: {exc}"

        if not matches:
            return f"No file named '{filename}' was found."

        return (
            f"Found {len(matches)} file(s):\n\n"
            + "\n".join(
                f"- {match}"
                for match in sorted(matches)
            )
        )

    def find_by_extension(self, extension: str) -> str:
        extension = extension.strip().lower()

        if not extension.startswith("."):
            extension = "." + extension

        matches = []

        try:
            for path in self.workspace.rglob("*"):

                if self._is_ignored(path):
                    continue

                if not path.is_file():
                    continue

                if path.suffix.lower() == extension:
                    matches.append(
                        str(path.relative_to(self.workspace))
                    )

        except (OSError, PermissionError) as exc:
            return f"Search failed: {exc}"

        if not matches:
            return f"No files with extension '{extension}' were found."

        return (
            f"Found {len(matches)} file(s):\n\n"
            + "\n".join(
                f"- {match}"
                for match in sorted(matches)
            )
        )

    def search_contents(self, search_text: str) -> str:
        search_text = search_text.strip()

        if not search_text:
            return "Please provide text to search for."

        matches = []

        binary_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".exe",
            ".dll",
            ".pyc",
            ".zip",
            ".pdf",
        }

        try:
            for path in self.workspace.rglob("*"):

                if self._is_ignored(path):
                    continue

                if not path.is_file():
                    continue

                if path.suffix.lower() in binary_extensions:
                    continue

                try:
                    content = path.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    )

                    if search_text.lower() in content.lower():
                        matches.append(
                            str(path.relative_to(self.workspace))
                        )

                except (
                    OSError,
                    PermissionError,
                    UnicodeError
                ):
                    continue

        except (OSError, PermissionError) as exc:
            return f"Content search failed: {exc}"

        if not matches:
            return (
                f"No files containing "
                f"'{search_text}' were found."
            )

        return (
            f"Found {len(matches)} file(s) containing "
            f"'{search_text}':\n\n"
            + "\n".join(
                f"- {match}"
                for match in sorted(matches)
            )
        )

    def read_file(self, relative_path: str) -> str:
        relative_path = relative_path.strip()
        relative_path = relative_path.replace("\\", "/")

        requested = (
            self.workspace / relative_path
        ).resolve()

        # Security boundary: never allow access outside
        # the AgentOS workspace.
        try:
            requested.relative_to(self.workspace)

        except ValueError:
            return (
                "Error: requested file is outside "
                "the AgentOS workspace."
            )

        if not requested.exists():
            return f"File not found: {relative_path}"

        if not requested.is_file():
            return f"Not a file: {relative_path}"

        try:
            content = requested.read_text(
                encoding="utf-8",
                errors="replace"
            )

            if len(content) > 20000:
                content = content[:20000]
                content += (
                    "\n\n"
                    "[File truncated after "
                    "20,000 characters.]"
                )

            return content

        except (OSError, PermissionError) as exc:
            return f"Could not read file: {exc}"