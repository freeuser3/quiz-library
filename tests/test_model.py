from dataclasses import asdict

from quiz_library.model import HomeworkEntry, Question, Paragraph, LLMConfig


def test_homework_entry_fields():
    e = HomeworkEntry(subject="География", content="параграф 6, вопросы 1-3")
    assert e.subject == "География"
    assert "параграф 6" in e.content


def test_question_fields():
    q = Question(subject="География", paragraph="6", paragraph_title="Газовая промышленность",
                 pages=(22, 25), text="Какой вопрос?")
    assert q.paragraph == "6"
    assert asdict(q)["paragraph"] == "6"


def test_paragraph_uses_key():
    p = Paragraph(key="6", title="Газовая", pages=(22, 25), blocks=[])
    assert p.key == "6"


def test_question_paragraph_is_str():
    q = Question(subject="ОБЗР", paragraph="6.1", paragraph_title="Х", pages=(1, 2), text="Q?")
    assert q.paragraph == "6.1"


def test_llm_config_frozen():
    cfg = LLMConfig(base_url="https://api.dslab.tech/v1", api_key="k", model="deepseek-v4.1-flash", timeout=20.0)
    assert cfg.timeout == 20.0
    try:
        cfg.model = "x"
    except Exception:
        return
    raise AssertionError("LLMConfig должен быть неизменяемым (frozen)")