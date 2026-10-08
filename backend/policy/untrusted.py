"""Helpers for keeping tool/file/log output visibly untrusted before LLM use."""

UNTRUSTED_PREFIX = "[UNTRUSTED_CONTENT source={source}]"
UNTRUSTED_SUFFIX = "[/UNTRUSTED_CONTENT]"


def mark_untrusted(content: object, source: str = "tool_output") -> str:
    text = str(content)
    return f"{UNTRUSTED_PREFIX.format(source=source)}\n{text}\n{UNTRUSTED_SUFFIX}"


def is_untrusted(content: object) -> bool:
    return isinstance(content, str) and content.startswith("[UNTRUSTED_CONTENT ") and content.rstrip().endswith(UNTRUSTED_SUFFIX)
