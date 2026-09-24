"""QuizService: задание домашки → текст параграфа → вопрос LLM."""
from __future__ import annotations

import logging
from pathlib import Path

from quiz_library.digests import DigestsRegistry, load_registry
from quiz_library.llm import LLMClient, LLMError
from quiz_library.model import HomeworkEntry, Question
from quiz_library.parser import parse_paragraph

logger = logging.getLogger(__name__)


class QuizService:
    def __init__(self, registry: DigestsRegistry, llm: LLMClient):
        self.registry = registry
        self.llm = llm

    @classmethod
    def from_config(cls, subjects_path: str | Path, llm: LLMClient) -> "QuizService":
        return cls(load_registry(subjects_path), llm)

    def patterns_for(self, subject: str) -> list[str]:
        entry = self.registry.subject(subject)
        return list(entry.paragraph_patterns) if entry else []

    def find_entry(self, entries: list[HomeworkEntry], subject: str) -> HomeworkEntry | None:
        for e in entries:
            if e.subject.lower() == subject.lower():
                return e
        return None

    async def question_for(self, entry: HomeworkEntry) -> Question | None:
        patterns = self.patterns_for(entry.subject)
        if not patterns:
            return None
        number = parse_paragraph(entry.content, patterns)
        if number is None:
            return None
        paragraph = self.registry.paragraph(entry.subject, number)
        if paragraph is None:
            return None
        try:
            text = await self.llm.generate_question(paragraph)
        except LLMError as exc:
            logger.warning("llm failed: %s", exc)
            return None
        return Question(
            subject=entry.subject,
            paragraph=number,
            paragraph_title=paragraph.title,
            pages=paragraph.pages,
            text=text,
        )