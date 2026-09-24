from dataclasses import asdict

from quiz_library.model import HomeworkEntry, Question, Paragraph, LLMConfig


def test_homework_entry_fields():
    e = HomeworkEntry(subject="География", content="параграф 6, вопросы 1-3")
    assert e.subject == "География"
    assert "параграф 6" in e.content


def test_question_fields():
    q = Question(subject="География", paragraph=6, paragraph_title="Газовая промышленность",
                 pages=(22, 25), text="Какой вопрос?")
    assert q.pages == (22, 25)
    assert asdict(q)["paragraph"] == 6


def test_paragraph_fields():
    p = Paragraph(number=6, title="Газовая промышленность", pages=(22, 25), blocks=[{"type": "page", "no": 22}])
    assert p.number == 6
    assert p.blocks[0]["type"] == "page"


def test_llm_config_frozen():
    cfg = LLMConfig(base_url="https://api.dslab.tech/v1", api_key="k", model="deepseek-v4.1-flash", timeout=20.0)
    assert cfg.timeout == 20.0
    try:
        cfg.model = "x"
    except Exception:
        return
    raise AssertionError("LLMConfig должен быть неизменяемым (frozen)")