from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HomeworkEntry:
    subject: str
    content: str


@dataclass
class Question:
    subject: str
    paragraph: int
    paragraph_title: str
    pages: tuple[int, int]
    text: str


@dataclass
class Paragraph:
    number: int
    title: str
    pages: tuple[int, int]
    blocks: list[dict]


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    timeout: float = 20.0