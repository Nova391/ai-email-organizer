"""Private, deterministic extractive email summarization."""
from __future__ import annotations

import re
from collections import Counter

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can",
    "do", "for", "from", "has", "have", "he", "her", "here", "his", "i",
    "if", "in", "is", "it", "its", "me", "my", "not", "of", "on", "or",
    "our", "please", "she", "so", "that", "the", "their", "them", "there",
    "they", "this", "to", "us", "was", "we", "were", "will", "with", "you", "your",
}
REPLY_MARKERS = (
    re.compile(r"^on .+wrote:$", re.IGNORECASE),
    re.compile(r"^-{2,}\s*(original message|forwarded message)\s*-{2,}$", re.IGNORECASE),
    re.compile(r"^from:\s+.+$", re.IGNORECASE),
)
SIGNATURE_MARKERS = (
    re.compile(r"^--\s*$"), re.compile(r"^sent from my\b", re.IGNORECASE),
    re.compile(r"^(best|kind) regards[,]?$", re.IGNORECASE),
)
BOILERPLATE = re.compile(
    r"\b(unsubscribe|manage (?:your )?preferences|view (?:this )?in (?:your )?browser|"
    r"privacy policy|terms (?:of use|and conditions)|all rights reserved|do not reply)\b",
    re.IGNORECASE,
)
ACTION_WORDS = re.compile(
    r"\b(action required|deadline|due|must|need(?:ed)?|confirm|approve|review|respond|"
    r"reply|schedule|meeting|payment|invoice|expires?|tomorrow|today|urgent)\b",
    re.IGNORECASE,
)

def _clean_email(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.replace("\r", "\n").split("\n"):
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if line.startswith(">") or any(pattern.match(line) for pattern in REPLY_MARKERS):
            break
        if any(pattern.match(line) for pattern in SIGNATURE_MARKERS):
            break
        line = re.sub(r"https?://\S+|www\.\S+", "", line)
        line = re.sub(r"\s+", " ", line).strip(" |")
        if line:
            lines.append(line)
    cleaned = " ".join(lines).strip()
    cleaned = re.split(r"\bOn .{1,200}? wrote:\s*", cleaned, maxsplit=1, flags=re.IGNORECASE)[0]
    cleaned = re.split(r"-{2,}\s*(?:original|forwarded) message\s*-{2,}", cleaned,
                       maxsplit=1, flags=re.IGNORECASE)[0]
    return cleaned.strip()

def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\s*[•●▪]\s+|\s+-\s+(?=[A-Z0-9])", text)
    return [part.strip(" -") for part in parts
            if part.strip(" -") and not BOILERPLATE.search(part)]

def _words(text: str) -> list[str]:
    return [word for word in re.findall(r"[^\W\d_]{2,}", text.lower(), re.UNICODE)
            if word not in STOP_WORDS]

def _clip(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars - 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    if not clipped:
        clipped = text[:max_chars - 1].rstrip()
    return clipped + "…"

def summarize(text: str | None, max_chars: int = 320, *, subject: str = "") -> str:
    """Return the most informative one or two sentences from an email."""
    if max_chars < 20:
        raise ValueError("max_chars must be at least 20")
    cleaned = _clean_email(text or "")
    if not cleaned:
        return _clip(re.sub(r"\s+", " ", subject).strip(), max_chars)
    candidates = _sentences(cleaned)
    if len(candidates) == 1:
        return _clip(candidates[0], max_chars)

    subject_words = set(_words(subject))
    frequencies = Counter(word for sentence in candidates for word in set(_words(sentence)))
    max_frequency = max(frequencies.values(), default=1)
    ranked: list[tuple[float, int, str]] = []
    for index, sentence in enumerate(candidates):
        words = _words(sentence)
        if not words:
            continue
        unique_words = set(words)
        relevance = sum(frequencies[word] / max_frequency for word in unique_words) / len(unique_words)
        subject_relevance = len(unique_words & subject_words) / max(1, len(subject_words))
        position_bonus = max(0.0, 0.45 - index * 0.07)
        action_bonus = 0.65 if ACTION_WORDS.search(sentence) else 0.0
        detail_bonus = 0.25 if re.search(r"\b\d+(?::\d+)?\b", sentence) else 0.0
        length_bonus = 0.2 if 35 <= len(sentence) <= 220 else 0.0
        score = relevance + 1.4 * subject_relevance + position_bonus + action_bonus + detail_bonus + length_bonus
        ranked.append((score, index, sentence))
    if not ranked:
        return _clip(cleaned, max_chars)
    selected = sorted(sorted(ranked, reverse=True)[:2], key=lambda item: item[1])
    return _clip(" ".join(item[2] for item in selected), max_chars)
