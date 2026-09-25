"""QuizService: задание домашки → текст параграфа → вопрос LLM."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from quiz_library.digests import DigestsRegistry, load_registry
from quiz_library.llm import LLMClient, LLMError
from quiz_library.match import search_paragraphs
from quiz_library.model import HomeworkEntry, Question
from quiz_library.parser import is_empty_homework, is_platform_homework, parse_paragraph

logger = logging.getLogger(__name__)


@dataclass
class Resolution:
    key: str | None
    reason: Literal["platform", "empty", "none", "number", "title", "ambiguous"]
    candidates: list[tuple[str, str, float]] = field(default_factory=list)

    @property
    def choice(self) -> str | None:
        if self.key is not None:
            return self.key
        if self.candidates:
            return self.candidates[0][0]
        return None


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

    def resolution(self, entry: HomeworkEntry) -> Resolution:
        meta = self.registry.subject(entry.subject)
        if meta is None:
            return Resolution(key=None, reason="none")
        content = entry.content
        if is_empty_homework(content):
            return Resolution(key=None, reason="empty")
        if is_platform_homework(content):
            return Resolution(key=None, reason="platform")

        logger.info("resolution: subject=%r content=%r", entry.subject, content[:80])
        patterns = self.patterns_for(entry.subject)
        number = parse_paragraph(content, patterns) if patterns else None
        titles = self.registry.titles(entry.subject)
        key = str(number) if number is not None else None
        if key is not None:
            p = self.registry.paragraph(entry.subject, key)
            if p is not None:
                logger.info("resolution: number -> key=%s", key)
                return Resolution(key=key, reason="number")

        # числовой каскад для «N.M»: ищем ключ «*.N», если единственный
        if number is not None and titles:
            matches = [k for k, _ in titles if k.endswith(f".{number}")]
            if len(matches) == 1:
                logger.info("resolution: cascade matches=%s -> key=%s", matches, matches[0])
                return Resolution(key=matches[0], reason="number")

        # затем title-поиск
        if not titles:
            # нет ни выжимки, ни номера
            logger.info("resolution: no titles -> none")
            return Resolution(key=None, reason="none")
        cands = search_paragraphs(titles, content, threshold=meta.search_threshold)
        if not cands:
            logger.info("resolution: candidates=[] -> none (threshold=%.2f)",
                        meta.search_threshold)
            return Resolution(key=None, reason="none")
        top5 = ", ".join(f"{k}={s:.2f}" for k, _, s in cands[:5])
        logger.info("resolution: candidates=[%s]", top5)
        if len(cands) == 1:
            logger.info("resolution: single candidate -> title key=%s", cands[0][0])
            return Resolution(key=cands[0][0], reason="title")
        top, second = cands[0][2], cands[1][2]
        if top / second >= meta.search_gap:
            logger.info("resolution: gap %.2f -> title key=%s", top / second, cands[0][0])
            return Resolution(key=cands[0][0], reason="title")
        if top < meta.search_llm_min:
            logger.info("resolution: top %.2f < llm_min %.2f -> title key=%s",
                        top, meta.search_llm_min, cands[0][0])
            return Resolution(key=cands[0][0], reason="title")  # сильных нет — ближайшее
        logger.info("resolution: ambiguous (top %.2f, second %.2f, gap %.2f)",
                    top, second, top / second)
        return Resolution(key=None, reason="ambiguous", candidates=cands)

    async def question_for(self, entry: HomeworkEntry) -> Question | None:
        res = self.resolution(entry)
        if res.reason in ("platform", "empty"):
            return None
        if res.key is None:
            if res.reason == "ambiguous" and self.llm is not None:
                try:
                    res.key = await self.llm.choose_paragraph(res.candidates, entry.content)
                    logger.info("arbiter: chose key=%s", res.key)
                except LLMError as exc:
                    logger.warning("llm arbiter failed: %s", exc)
                    res.key = None
            if res.key is None:
                return None
        paragraph = self.registry.paragraph(entry.subject, res.key)
        if paragraph is None:
            return None
        try:
            text = await self.llm.generate_question(paragraph)
        except LLMError as exc:
            logger.warning("llm failed: %s", exc)
            return None
        logger.info("question: subject=%r key=%s title=%r pages=%s",
                    entry.subject, res.key, paragraph.title, paragraph.pages)
        return Question(
            subject=entry.subject,
            paragraph=res.key,
            paragraph_title=paragraph.title,
            pages=paragraph.pages,
            text=text,
        )