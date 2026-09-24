"""Голосовое оформление вопроса."""
from __future__ import annotations

from quiz_library.model import Question


def question_to_voice(question: Question) -> str:
    return f"Вопрос по {question.subject}, параграф {question.paragraph}: {question.text}"