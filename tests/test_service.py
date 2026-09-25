import os
from pathlib import Path

import pytest

from quiz_library.digests import DigestsRegistry, SubjectEntry
from quiz_library.llm import LLMError
from quiz_library.model import HomeworkEntry, LLMConfig, Paragraph, Question
from quiz_library.service import QuizService


class FakeLLM:
    def __init__(self, text=None, error=None):
        self.text = text or "Готовый вопрос?"
        self.error = error

    async def generate_question(self, paragraph):
        if self.error:
            raise self.error
        return self.text


def _registry():
    p = Paragraph(key="6", title="Газовая промышленность", pages=(22, 25),
                  blocks=[{"type": "text", "lines": ["Газ важен.", "Газ горит."]}])

    class R:
        def __init__(self):
            self._p = p

        def subject(self, name):
            if name.lower() != "география":
                return None
            return SubjectEntry(book="b", digest_path="x.json", paragraph_patterns=["параграф", "§"])

        def titles(self, name):
            return [("6", p.title)]

        def paragraph(self, subject, key):
            if subject.lower() == "география" and key == "6":
                return self._p
            return None

    return R()


async def test_find_entry_case_insensitive():
    svc = QuizService(_registry(), FakeLLM())
    entries = [HomeworkEntry(subject="география", content="параграф 6")]
    assert svc.find_entry(entries, "География") is entries[0]


async def test_find_entry_missing_returns_none():
    svc = QuizService(_registry(), FakeLLM())
    assert svc.find_entry([], "География") is None


async def test_question_for_full_flow():
    svc = QuizService(_registry(), FakeLLM(text="Вопрос?"))
    q = await svc.question_for(HomeworkEntry(subject="География", content="параграф 6, вопросы 1-3"))
    assert isinstance(q, Question)
    assert q.paragraph == "6"
    assert q.paragraph_title == "Газовая промышленность"
    assert q.pages == (22, 25)
    assert q.text == "Вопрос?"


async def test_question_for_no_subject():
    svc = QuizService(_registry(), FakeLLM())
    assert await svc.question_for(HomeworkEntry(subject="История", content="параграф 6")) is None


async def test_question_for_no_paragraph():
    svc = QuizService(_registry(), FakeLLM())
    assert await svc.question_for(HomeworkEntry(subject="География", content="упражнение 3")) is None


async def test_question_for_missing_in_digest():
    svc = QuizService(_registry(), FakeLLM())
    assert await svc.question_for(HomeworkEntry(subject="География", content="параграф 99")) is None


async def test_question_for_llm_error_returns_none():
    svc = QuizService(_registry(), FakeLLM(error=LLMError("boom")))
    assert await svc.question_for(HomeworkEntry(subject="География", content="параграф 6")) is None


async def test_from_config_builds_service(tmp_path):
    import json
    dg = tmp_path / "g.json"
    dg.write_text(json.dumps({"meta": {}, "paragraphs": {
        "6": {"title": "T", "pages": {"start": 22, "end": 25},
              "blocks": [{"type": "text", "lines": ["X."]}]}}}, ensure_ascii=False), encoding="utf-8")
    sp = tmp_path / "subjects.json"
    sp.write_text(json.dumps({"География": {"book": "b", "digest": str(dg),
                                            "paragraph_patterns": ["параграф"]}}, ensure_ascii=False), encoding="utf-8")
    svc = QuizService.from_config(sp, FakeLLM(text="Q?"))
    q = await svc.question_for(HomeworkEntry(subject="География", content="параграф 6"))
    assert q and q.text == "Q?"


class R2:
    """Registry-fake с маленьким списком тем (ОБЗР) и match_paragraphs=False."""

    def __init__(self, titles, match_paragraphs=False, search_threshold=None,
                 search_llm_min=None):
        self._titles = titles
        self._match = match_paragraphs
        self._thr = search_threshold
        self._llm_min = search_llm_min

    def subject(self, name):
        kw = {}
        if self._thr is not None:
            kw["search_threshold"] = self._thr
        if self._llm_min is not None:
            kw["search_llm_min"] = self._llm_min
        return SubjectEntry(book="b", digest_path="x.json", paragraph_patterns=["параграф", "§", "тема"],
                            match_paragraphs=self._match, **kw)

    def titles(self, name):
        return self._titles

    def paragraph(self, name, key):
        for k, t in self._titles:
            if k == key:
                return Paragraph(key=key, title=t, pages=(1, 2), blocks=[])
        return None


async def test_resolution_no_match():
    svc = QuizService(R2([("6.1", "Общие представления о здоровье"),
                          ("7.5", "Безопасное поведение и современные увлечения молодёжи")]), FakeLLM())
    # редкий токен отсутствует в заголовках → кандидатов нет → none
    r = svc.resolution(HomeworkEntry(subject="ОБЗР", content="В горах Кавказа"))
    assert r.reason == "none"


async def test_resolution_exact_title():
    svc = QuizService(R2([("5.3", "Пожарная безопасность в природной среде")]), FakeLLM())
    r = svc.resolution(HomeworkEntry(subject="ОБЗР", content="Пожарная безопасность в природной среде"))
    assert r.reason == "title"
    assert r.key == "5.3"


async def test_resolution_number_first():
    svc = QuizService(R2([("6", "Газовая промышленность")], match_paragraphs=True), FakeLLM())
    r = svc.resolution(HomeworkEntry(subject="ОБЗР", content="параграф 6"))
    assert r.reason == "number"
    assert r.key == "6"


async def test_resolution_platform_marker():
    svc = QuizService(R2([]), FakeLLM())
    r = svc.resolution(HomeworkEntry(subject="Физика", content="Сириус, урок 8"))
    assert r.reason == "platform"


async def test_resolution_empty_placeholder():
    svc = QuizService(R2([]), FakeLLM())
    r = svc.resolution(HomeworkEntry(subject="ОБЗР", content="Домашнее задание: ---Не указана---"))
    assert r.reason == "empty"


async def test_question_for_uses_arbiter_when_ambiguous():
    class Pick(FakeLLM):
        async def choose_paragraph(self, candidates, query):
            return "7.8"

    svc = QuizService(R2([("7.5", "Безопасное поведение и современные увлечения молодёжи"),
                          ("7.8", "Безопасное поведение в цифровой среде")],
                         search_threshold=0.15, search_llm_min=0.15), FakeLLM(text="Q?"))
    svc.llm = Pick()
    q = await svc.question_for(HomeworkEntry(subject="ОБЗР", content="безопасное поведение"))
    assert q and q.paragraph == "7.8"


OBZR_SUBJECTS = os.environ.get("OBZR_SUBJECTS_PATH")


# Интеграция с реальной выжимкой ОБЗР: subjects.json из GeoRag содержит
# относительные digest-пути — прогон должен идти из каталога GeoRag
# (PYTHONPATH=...quiz-library), digests/obzr.json резолвится относительно CWD.
@pytest.mark.skipif(not OBZR_SUBJECTS, reason="real OBZR subjects.json not configured")
async def test_resolution_obzr_natural_environment_not_digital():
    svc = QuizService.from_config(Path(OBZR_SUBJECTS), FakeLLM())
    r = svc.resolution(HomeworkEntry(subject="ОБЗР",
                                     content="Правила безопасного поведения в природной среде"))
    assert r.key != "8.1"
    assert r.reason in ("title", "ambiguous")


@pytest.mark.skipif(not OBZR_SUBJECTS, reason="real OBZR subjects.json not configured")
async def test_resolution_obzr_hills_finds_gora():
    svc = QuizService.from_config(Path(OBZR_SUBJECTS), FakeLLM())
    r = svc.resolution(HomeworkEntry(subject="ОБЗР", content="Безопасное поведение в горах"))
    assert r.key == "5.4"


@pytest.mark.skipif(not OBZR_SUBJECTS, reason="real OBZR subjects.json not configured")
async def test_resolution_obzr_water_and_defense():
    svc = QuizService.from_config(Path(OBZR_SUBJECTS), FakeLLM())
    r1 = svc.resolution(HomeworkEntry(subject="ОБЗР",
                                      content="Правила безопасного поведения на водоёмах"))
    assert r1.reason == "title" and r1.key == "5.5"
    r2 = svc.resolution(HomeworkEntry(subject="ОБЗР", content="Оборона страны"))
    assert r2.key == "10.2"


@pytest.mark.skipif(not OBZR_SUBJECTS, reason="real OBZR subjects.json not configured")
async def test_resolution_obzr_module_topic_number():
    svc = QuizService.from_config(Path(OBZR_SUBJECTS), FakeLLM())
    r = svc.resolution(HomeworkEntry(subject="ОБЗР", content="тема 8.1, вопросы 1-2"))
    assert r.reason == "number" and r.key == "8.1"


@pytest.mark.skipif(not OBZR_SUBJECTS, reason="real OBZR subjects.json not configured")
async def test_resolution_obzr_conflicts_goes_to_arbiter():
    svc = QuizService.from_config(Path(OBZR_SUBJECTS), FakeLLM())
    r = svc.resolution(HomeworkEntry(subject="ОБЗР", content="прочитать тему про конфликты"))
    assert r.reason == "ambiguous"
    assert any(k in ("7.2", "7.4") for k, _, _ in r.candidates)


async def test_resolution_logs_title_candidates(caplog):
    import logging

    svc = QuizService(
        R2([("5.3", "Пожарная безопасность в природной среде"),
            ("7.8", "Безопасное поведение в цифровой среде")], search_threshold=0.15),
        FakeLLM(),
    )
    with caplog.at_level(logging.INFO, logger="quiz_library.service"):
        r = svc.resolution(
            HomeworkEntry(subject="ОБЗР", content="Пожарная безопасность в природной среде")
        )
    assert r.reason == "title" and r.key == "5.3"
    msgs = [rec.message for rec in caplog.records]
    assert any("resolution" in m and "candidates=" in m for m in msgs)


async def test_resolution_logs_number_step(caplog):
    import logging

    svc = QuizService(R2([("6", "Газовая промышленность")], match_paragraphs=True), FakeLLM())
    with caplog.at_level(logging.INFO, logger="quiz_library.service"):
        r = svc.resolution(HomeworkEntry(subject="ОБЗР", content="параграф 6"))
    assert r.reason == "number" and r.key == "6"
    msgs = [rec.message for rec in caplog.records]
    assert any("resolution" in m and "number" in m and "key=6" in m for m in msgs)