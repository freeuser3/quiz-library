from __future__ import annotations

import re
from collections import Counter

DEFAULT_THRESHOLD = 0.45
DEFAULT_GAP = 1.3
DEFAULT_LLM_MIN = 0.25

_LEADER = re.compile(r"^\s*(?:тема|темы|модуль|модули)\s*\d+\s*[\.\s]\s*", re.IGNORECASE)
_TOKEN = re.compile(r"[а-яёa-zА-ЯЁA-Z0-9]+")


def normalize_title(text: str) -> str:
    text = _LEADER.sub("", text)
    lowered = " ".join(_TOKEN.findall(text.lower()))
    return re.sub(r"\s+", " ", lowered).strip()


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def rare_terms(titles: list[str]) -> set[str]:
    normed = [normalize_title(t) for t in titles]
    freq = Counter(w for t in normed for w in tokenize(t))
    return {w for w, c in freq.items() if c < 2}


def title_similarity(query_tokens: list[str], title_tokens: list[str], rare: set[str]) -> float:
    q = set(query_tokens)
    t = set(title_tokens)
    rare_common = len(q & t & rare)
    common = len(q & t)
    return 0.4 * rare_common + 0.1 * common


def search_paragraphs(titles, query: str, *, threshold: float = DEFAULT_THRESHOLD) -> list[tuple[str, str, float]]:
    qt = tokenize(query)
    if not qt:
        return []
    rare = rare_terms([t for _, t in titles])
    results = []
    for key, title in titles:
        tt = tokenize(normalize_title(title))
        s = title_similarity(qt, tt, rare)
        if s >= threshold:
            results.append((key, normalize_title(title), round(s, 2)))
    results.sort(key=lambda x: x[2], reverse=True)
    return results
