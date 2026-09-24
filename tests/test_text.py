from quiz_library.model import Paragraph
from quiz_library.text import paragraph_plain_text


def _para(blocks):
    return Paragraph(number=6, title="t", pages=(22, 25), blocks=blocks)


def test_joins_lines_in_block_order_skipping_page():
    p = _para([
        {"type": "page", "no": 22},
        {"type": "text", "lines": ["Природный газ представляет собой смесь.", "Газ горит."]},
        {"type": "page", "no": 23},
        {"type": "text", "lines": ["Второй блок."]},
    ])
    assert paragraph_plain_text(p).count("\n") == 2
    assert "Второй блок." in paragraph_plain_text(p)


def test_joins_lowercase_hyphen_split():
    p = _para([{"type": "text", "lines": ["газопрово-", "да", "магистраль"]}])
    assert paragraph_plain_text(p) == "газопровода\nмагистраль"


def test_joins_caps_hyphen_split():
    p = _para([{"type": "memo", "lines": ["СТРАТЕГИЧЕ-", "СКИЙ РЕСУРС"]}])
    assert paragraph_plain_text(p) == "СТРАТЕГИЧЕСКИЙ РЕСУРС"


def test_keeps_hyphen_before_capital_in_lowercase_context():
    p = _para([{"type": "text", "lines": ["Юго-", "Запад"]}])
    assert paragraph_plain_text(p) == "Юго-\nЗапад"


def test_image_caption_lines_joined_inline():
    p = _para([{"type": "image", "lines": ["Рис. 10. Страны — лидеры (млрд м3)", "в 2019 г."]}])
    assert paragraph_plain_text(p) == "Рис. 10. Страны — лидеры (млрд м3) в 2019 г."


def test_empty_blocks_returns_empty():
    assert paragraph_plain_text(_para([])) == ""