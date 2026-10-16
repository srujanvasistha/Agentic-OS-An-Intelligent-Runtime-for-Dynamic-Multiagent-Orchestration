import re
from search.semantic_search import semantic_engine


class TaskRouter:
    """
    Determines which capability best matches a user task.
    Understands prompt semantics and intent conceptually rather than
    relying solely on literal keyword presence, while retaining
    keyword rules for deterministic test coverage.
    """

    def classify(self, prompt: str, image_url: str | None = None) -> str:
        text = prompt.lower().strip()

        # If user explicitly provided an uploaded image, check if this is an image task
        has_image = bool(image_url and str(image_url).strip())

        # Direct regex patterns for image analysis (both US & UK spellings)
        img_analysis_patterns = [
            r"\b(?:analyse|analyze|inspect|examine|describe|explain|read|check|audit|review)\b.*?\b(?:image|picture|photo|photograph|screenshot|graphic|visual|upload)\b",
            r"\bwhat(?:'s|\s+is)\s+(?:there\s+in|in|on|shown\s+in)\s+(?:the|this|my|that)?\s*(?:image|picture|photo|screenshot)\b",
            r"\b(?:analyse|analyze)\b.*?\b(?:tell|show|give)\s+(?:me\s+)?(?:the\s+)?output\b",
            r"\b(?:image|picture|photo)\s+(?:analysis|breakdown|telemetry|details|output|summary)\b",
            r"\b(?:extract\s+text|ocr)\b",
        ]
        for pat in img_analysis_patterns:
            if re.search(pat, text):
                return "image_analysis"

        # Direct regex patterns for image generation / synthesis
        img_generation_patterns = [
            r"\b(?:generate|create|draw|render|make|produce|synthesize)\s+(?:an?\s+)?(?:image|picture|photo|diagram|flowchart|sketch|illustration|visual|graphic|artwork|figure)\b",
            r"\b(?:diagram|flowchart|architecture|chart|illustration|sketch|visual)\s+of\b",
            r"\b(?:draw|paint|sketch)\s+(?:a|an|the)\b",
            r"\bimage\s+of\b",
        ]
        for pat in img_generation_patterns:
            if re.search(pat, text):
                return "image_generation"

        # If an image is attached and the prompt is an open question or visual query
        if has_image:
            non_image_commands = [
                "list files", "search files", "count files", "create file", "write file",
                "cpu", "memory", "ram", "vulnerability", "sandbox", "audit security"
            ]
            if not any(cmd in text for cmd in non_image_commands):
                return "image_analysis"

        # Conversational / conceptual queries default to general_questions
        general_starters = ["what is", "what are", "explain", "describe", "tell me", "who is", "why is", "how does an", "how do"]
        if any(text.startswith(p) for p in general_starters):
            action_verbs = [
                "monitor", "cpu", "memory usage", "vulnerability", "scan",
                "list files", "search files", "inspect files", "break down",
                "generate image", "draw", "create image", "image", "picture",
                "diagram", "chart", "analyze image", "analyse image", "photo", "figure", "visual",
                "analyse", "analyze", "screenshot"
            ]
            if not any(v in text for v in action_verbs):
                return "general_questions"

        # 1. Semantic intent analysis (understands prompt conceptually)
        best_cap, confidence, scores = semantic_engine.classify_intent(prompt)
        if confidence >= 0.12 and best_cap != "general_questions":
            return best_cap

        # 2. Keyword fallback for exact phrase matches
        planning_keywords = [
            "plan",
            "planning",
            "subtask",
            "subtasks",
            "break down",
            "decompose",
            "decomposition",
            "dependencies",
            "dependency",
            "assign agent",
            "orchestrate",
            "orchestration",
            "workflow",
            "pipeline",
            "multi-step",
            "combine output",
        ]

        monitoring_keywords = [
            "monitor",
            "monitoring",
            "cpu",
            "memory",
            "ram",
            "telemetry",
            "metrics",
            "anomaly",
            "anomalies",
            "operational report",
            "health check",
            "system status",
            "queue status",
            "queue length",
            "latency metrics",
            "diagnostics",
            "resource usage",
            "utilization",
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
            "create",
            "write",
            "save",
        ]

        image_analysis_keywords = [
            "analyze image",
            "analyse image",
            "analyze this image",
            "analyse this image",
            "analyze my image",
            "analyse my image",
            "analyze the image",
            "analyse the image",
            "inspect image",
            "inspect this image",
            "read image",
            "describe image",
            "describe this image",
            "what is this image",
            "what is in this picture",
            "what is there in the image",
            "what is in the image",
            "what does this image show",
            "explain this image",
            "explain this picture",
            "explain the image",
            "image analysis",
            "examine image",
            "examine picture",
            "examine the image",
            "image info",
            "image details",
            "uploaded image",
            "image breakdown",
            "tell the output",
            "tell me what is in the image",
            "what do you see in the image",
        ]

        for keyword in image_analysis_keywords:
            if keyword in text:
                return "image_analysis"

        image_keywords = [
            "generate image",
            "create image",
            "generate an image",
            "create an image",
            "draw ",
            "draw a ",
            "render image",
            "make an image",
            "generate visual",
            "visualize diagram",
            "produce image",
            "generate graphic",
            "generate photo",
            "generate picture",
            "image of",
            "diagram of",
            "flowchart of",
            "architecture of",
            "chart of",
            "illustration of",
            "illustration",
            "sketch",
            "generate chart",
            "generate figure",
            "generate art",
            "image generation",
            "paint ",
        ]

        for keyword in image_keywords:
            if keyword in text:
                return "image_generation"

        for keyword in planning_keywords:
            if keyword in text:
                return "task_planning"

        for keyword in monitoring_keywords:
            if keyword in text:
                return "monitoring"

        for keyword in security_keywords:
            if keyword in text:
                return "security_analysis"

        for keyword in file_keywords:
            if keyword in text:
                return "file_search"

        if confidence >= 0.06:
            return best_cap

        return "general_questions"