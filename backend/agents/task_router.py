class TaskRouter:
    """
    Determines which capability best matches a user task.
    """

    def classify(self, prompt: str) -> str:
        text = prompt.lower().strip()

        file_keywords = [
            "file",
            "files",
            "folder",
            "folders",
            "directory",
            "directories",
            "workspace",
            "read ",
            "find ",
            "search files",
            "list files",
            "python files",
            "markdown files",
            "json files",
        ]

        security_keywords = [
            "security",
            "secure",
            "vulnerability",
            "vulnerabilities",
            "attack",
            "threat",
            "risk",
            "permission",
            "authentication",
            "authorization",
            "malware",
        ]

        for keyword in security_keywords:
            if keyword in text:
                return "security_analysis"

        for keyword in file_keywords:
            if keyword in text:
                return "file_search"

        return "general_questions"