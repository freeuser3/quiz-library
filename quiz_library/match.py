from __future__ import annotations

import re

DEFAULT_THRESHOLD = 0.45
DEFAULT_GAP = 1.3
DEFAULT_LLM_MIN = 0.25

_LEADER_FULL = re.compile(
    r"^\s*(?:модул\w*\s*\d+\s*\.?\s*)?(?:тем\w*\s*\d+\s*\.?\s*)?", re.IGNORECASE)
_TOKEN = re.compile(r"[а-яёa-zА-ЯЁA-Z0-9]+")


def _token_class(word: str) -> str:
    word = word.lower().replace("ё", "е")
    return word[:4]


def normalize_title(text: str) -> str:
    text = _LEADER_FULL.sub("", text)
    lowered = " ".join(_TOKEN.findall(text.lower()))
    return re.sub(r"\s+", " ", lowered).strip()


def tokenize(text: str) -> list[str]:
    return [_token_class(t) for t in _TOKEN.findall(text.lower())]


def title_similarity(query_tokens: list[str], title_tokens: list[str]) -> float:
    q = set(query_tokens)
    if not q:
        return 0.0
    return len(q & set(title_tokens)) / len(q)


def search_paragraphs(titles, query: str, *, threshold: float = DEFAULT_THRESHOLD) -> list[tuple[str, str, float]]:
    qt = tokenize(query)
    if not qt:
        return []
    results = []
    for key, title in titles:
        tt = tokenize(title)
        s = title_similarity(qt, tt)
        if s >= threshold:
            results.append((key, normalize_title(title), round(s, 2)))
    results.sort(key=lambda x: x[2], reverse=True)
    return results
