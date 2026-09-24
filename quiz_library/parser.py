"""Разбор номера параграфа из строки домашнего задания."""
from __future__ import annotations

import re

_MAX_PARA = 999


def parse_paragraph(text: str, patterns: list[str]) -> int | None:
    """Первый номер после любого из заданных паттернов («параграф», «§», …).

    Паттерн понимается как префикс: за ним следует необязательное число.
    Порядок паттернов важен: из списка строится один regex с |, поэтому
    длинные («параграфа») ставятся первыми, чтобы они выигрывали у коротких.
    """
    if not text or not patterns:
        return None
    patterns = sorted(patterns, key=len, reverse=True)
    expr = "(?:" + "|".join(re.escape(p) for p in patterns) + r")\s*(\d{1,3})\b"
    m = re.search(expr, text, re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1))


_PLATFORM_WORDS = {
    "сириус", "урок", "урока", "учи.ру", "учиру", "якласс", "реш",
    "инфоурок", "сдам гиа", "фоксфорд", "скайсмарт", "прикрепл",
}
_URL = re.compile(r"https?://\S+", re.IGNORECASE)
_EMPTY = re.compile(r"---\s*н\s*е\s*указан", re.IGNORECASE)


def is_platform_homework(text: str) -> bool:
    if not text:
        return False
    if _URL.search(text):
        return True
    low = text.lower()
    return any(w in low for w in _PLATFORM_WORDS)


def is_empty_homework(text: str) -> bool:
    return bool(_EMPTY.search(text))


def has_para_marker_without_number(text: str, patterns: list[str]) -> bool:
    if not text or not patterns:
        return False
    low = text.lower()
    for p in patterns:
        if p.lower() in low:
            # маркер есть, а числа после него нет
            after = low.split(p.lower(), 1)[1]
            if not re.search(r"\d", after):
                return True
    return False