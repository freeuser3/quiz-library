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
    m = re.search(expr, text)
    if not m:
        return None
    return int(m.group(1))