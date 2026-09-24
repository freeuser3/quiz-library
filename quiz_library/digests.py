"""Загрузка subjects.json и выжимок учебников в объектную модель."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from quiz_library.model import Paragraph

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubjectEntry:
    book: str
    digest_path: str
    paragraph_patterns: list[str]
    match_paragraphs: bool = True
    search_threshold: float = 0.45
    search_gap: float = 1.3
    search_llm_min: float = 0.25


def load_subjects(path: str | Path) -> dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_registry(subjects_path: str | Path) -> "DigestsRegistry":
    raw = load_subjects(subjects_path)
    entries = {}
    for name, cfg in raw.items():
        entries[name] = SubjectEntry(
            book=cfg.get("book", ""),
            digest_path=cfg["digest"],
            paragraph_patterns=list(cfg.get("paragraph_patterns", [])),
            match_paragraphs=bool(cfg.get("match_paragraphs", True)),
            search_threshold=float(cfg.get("search_threshold", 0.45)),
            search_gap=float(cfg.get("search_gap", 1.3)),
            search_llm_min=float(cfg.get("search_llm_min", 0.25)),
        )
    return DigestsRegistry(entries)


class DigestsRegistry:
    def __init__(self, entries: dict[str, SubjectEntry]):
        self._entries = entries
        self._cache: dict[str, dict | None] = {}

    def subject(self, name: str) -> SubjectEntry | None:
        for key, entry in self._entries.items():
            if key.lower() == name.lower():
                return entry
        return None

    def _digest_json(self, subject: str) -> dict | None:
        if subject in self._cache:
            return self._cache[subject]
        entry = self.subject(subject)
        if entry is None:
            self._cache[subject] = None
            return None
        try:
            with open(entry.digest_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            logger.warning("digest not loadable: %s (%s)", entry.digest_path, exc)
            data = None
        self._cache[subject] = data
        return data

    def paragraph(self, subject: str, key: str) -> Paragraph | None:
        data = self._digest_json(subject)
        if not data:
            return None
        raw = data.get("paragraphs", {}).get(str(key))
        if not raw:
            return None
        pages = raw.get("pages", {})
        return Paragraph(
            key=str(key),
            title=raw.get("title", ""),
            pages=(int(pages.get("start", 0)), int(pages.get("end", 0))),
            blocks=raw.get("blocks", []),
        )

    def titles(self, subject: str) -> list[tuple[str, str]]:
        data = self._digest_json(subject)
        if not data:
            return []
        return [(k, p.get("title", "")) for k, p in data.get("paragraphs", {}).items()]

    def subjects_meta(self) -> dict[str, SubjectEntry]:
        return dict(self._entries)