"""Fast, deterministic extractive summaries (no external API required)."""
import re

def summarize(text: str | None, max_chars: int = 240) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    result = ""
    for sentence in sentences:
        candidate = f"{result} {sentence}".strip()
        if len(candidate) > max_chars:
            break
        result = candidate
        if len(result) >= max_chars * 0.6:
            break
    if not result:
        result = cleaned[:max_chars].rstrip()
    if len(result) < len(cleaned) and not result.endswith((".", "!", "?", "…")):
        result = result.rstrip(" ,;:") + "…"
    return result
