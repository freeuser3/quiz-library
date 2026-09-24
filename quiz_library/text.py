"""Склейка текста параграфа из blocks (без сохранения plain_text в JSON)."""
from __future__ import annotations

from quiz_library.model import Paragraph


def paragraph_plain_text(paragraph: Paragraph) -> str:
    lines = []
    for b in paragraph.blocks:
        if b["type"] == "page":
            continue
        if b["type"] == "image":
            # подпись рисунка — строки подряд через пробел
            lines.append(" ".join(b["lines"]))
        else:
            lines.extend(b["lines"])
    joined = []
    for s in lines:
        prev = joined[-1] if joined else ""
        prev_body = prev[:-1] if prev.endswith("-") else ""
        if prev.endswith("-") and s and (
            not s[0].isupper() or (prev_body and prev_body.isupper())
        ):
            joined[-1] = prev_body + s   # перенос слова («газопрово-»+«да», «СТРАТЕГИЧЕ-»+«СКИЙ»)
        else:
            joined.append(s)             # дефис перед заглавной сохраняется («Юго-»+«Запад»)
    return "\n".join(joined)