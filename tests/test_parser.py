import pytest

from quiz_library.parser import parse_paragraph


def test_plain_phrase():
    assert parse_paragraph("параграф 6", ["параграф", "параграфа", "§"]) == 6


def test_capitalized_phrase():
    # реальное задание может начинаться с заглавной «Параграф 6»
    assert parse_paragraph("Параграф 6", ["параграф", "§"]) == 6


def test_paragraph_with_questions_suffix():
    assert parse_paragraph("прочитать параграф 6, вопросы 1-3", ["параграф", "§"]) == 6


def test_section_symbol_no_space():
    assert parse_paragraph("выучить §6", ["параграф", "§"]) == 6


def test_section_symbol_with_space():
    assert parse_paragraph("задание § 6", ["параграф", "§"]) == 6


def test_paragrapha_form():
    assert parse_paragraph("начиная с параграфа 17", ["параграф", "параграфа", "§"]) == 17


def test_no_paragraph_returns_none():
    assert parse_paragraph("выполнить упражнение 3", ["параграф", "§"]) is None


def test_empty_text_returns_none():
    assert parse_paragraph("", ["параграф", "§"]) is None


def test_regex_special_chars_in_pattern_escaped():
    # паттерн может содержать спецсимволы regex; они не должны ломать парсинг
    assert parse_paragraph("§ 6 после точки.", ["§"]) == 6


def test_semantic_check_overlapping_words():
    # «параграфа» начинается с «параграф»; оба паттерна не дают двойного матча
    assert parse_paragraph("параграфа 3", ["параграф", "параграфа", "§"]) == 3