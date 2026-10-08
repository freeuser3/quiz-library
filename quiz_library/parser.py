"""Разбор номера параграфа из строки домашнего задания."""
from __future__ import annotations

import re

_MAX_PARA = 999


def parse_paragraph(text: str, patterns: list[str]) -> int | str | None:
    """Первый номер после любого из заданных паттернов («параграф», «§», …).

    Паттерн понимается как префикс: за ним следует необязательное число.
    Номер может быть составным «N.M» (модуль.тема для ОБЗР) — тогда
    возвращается строка «N.M», иначе целое int.
    Порядок паттернов важен: из списка строится один regex с |, поэтому
    длинные («параграфа») ставятся первыми, чтобы они выигрывали у коротких.
    """
    if not text or not patterns:
        return None
    patterns = sorted(patterns, key=len, reverse=True)
    expr = "(?:" + "|".join(re.escape(p) for p in patterns) + r")\s*(\d{1,3}(?:\.\d{1,2})?)\b"
    m = re.search(expr, text, re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1)
    return raw if "." in raw else int(raw)


def parse_paragraphs(text: str, patterns: list[str], max_paragraphs: int = 5) -> list[int | str]:
    """Все номера параграфов из задания: диапазоны «9-10» раскрываются,
    перечисления «9, 10» и «9 и 10» собираются. Не больше max_paragraphs.

    Собираются только числа, идущие сразу за маркером («параграф», «§», …):
    «вопросы 1-3» не считаются. Составной номер «N.M» (ОБЗР) не раскрывается.
    """
    if not text or not patterns:
        return []
    patterns = sorted(patterns, key=len, reverse=True)
    markers = "(?:" + "|".join(re.escape(p) for p in patterns) + r")"
    n = r"\d{1,3}(?:\.\d{1,2})?"
    g = (
        n + r"\b"
        r"(?:\s*[–—-]\s*" + n + r"\b"
        r"|\s*,\s*" + n + r"\b"
        r"|\s+и\s+" + n + r"\b)*"
    )
    expr = markers + r"\s*(" + g + r")"
    result: list[int | str] = []
    for m in re.finditer(expr, text, re.IGNORECASE):
        for v in _expand_group(m.group(1), max_paragraphs - len(result)):
            result.append(v)
            if len(result) >= max_paragraphs:
                return result
    return result


def _expand_group(group: str, limit: int) -> list[int | str]:
    tokens = re.findall(r"\d{1,3}(?:\.\d{1,2})?|[–—-]", group)
    items: list[int | str] = []
    i = 0
    while i < len(tokens) and len(items) < limit:
        t = tokens[i]
        if t in "–—-":
            i += 1
            continue
        if (i + 2 < len(tokens) and tokens[i + 1] in "–—-"
                and t.isdigit() and tokens[i + 2].isdigit()):
            a, b = int(t), int(tokens[i + 2])
            while a <= b and len(items) < limit:
                items.append(a)
                a += 1
            i += 3
        else:
            items.append(t if "." in t else int(t))
            i += 1
    return items


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