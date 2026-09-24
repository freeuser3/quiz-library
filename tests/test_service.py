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
    p = Paragraph(number=6, title="Газовая промышленность", pages=(22, 25),
                  blocks=[{"type": "text", "lines": ["Газ важен.", "Газ горит."]}])

    class R:
        def __init__(self):
            self._p = p

        def subject(self, name):
            if name.lower() != "география":
                return None
            return SubjectEntry(book="b", digest_path="x.json", paragraph_patterns=["параграф", "§"])

        def paragraph(self, subject, number):
            if subject.lower() == "география" and number == 6:
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
    assert q.paragraph == 6
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