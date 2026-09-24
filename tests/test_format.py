from quiz_library.format import question_to_voice
from quiz_library.model import Question


def test_voice_phrase():
    q = Question(subject="География", paragraph=6, paragraph_title="Газовая промышленность",
                 pages=(22, 25), text="Какой фактор размещения важнее?")
    out = question_to_voice(q)
    assert "География" in out
    assert "6" in out
    assert "Какой фактор размещения важнее?" in out