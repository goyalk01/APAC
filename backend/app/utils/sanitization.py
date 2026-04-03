import re

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"reveal\s+system\s+prompt",
    r"exfiltrate",
    r"bypass\s+security",
]


def sanitize_text(text: str) -> str:
    cleaned = text.replace("\x00", "").strip()
    return cleaned


def detect_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in PROMPT_INJECTION_PATTERNS)
