import pytest

from quiz_library.parser import (
    parse_paragraph,
    is_platform_homework,
    is_empty_homework,
    has_para_marker_without_number,
)


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


def test_topic_with_module_number_keeps_dot():
    assert parse_paragraph("тема 8.1", ["тема", "темы", "модуль", "модули", "параграф", "параграфа", "§"]) == "8.1"


def test_topic_plain_number_still_int():
    assert parse_paragraph("тема 8", ["тема", "темы"]) == 8


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


def test_platform_sirius():
    assert is_platform_homework("Сириус, урок 8")
    assert is_platform_homework("В прикрепленном файле выполнить…")


def test_platform_http_link():
    assert is_platform_homework("https://4ege.ru/gia-matematika/80634.html")


def test_platform_negative():
    assert not is_platform_homework("Газовая промышленность. Пересказ § 6")


def test_empty_placeholder():
    assert is_empty_homework("---Не указана---")
    assert not is_empty_homework("")


def test_marker_without_number_true():
    assert has_para_marker_without_number("параграф про факторы скорости реакции", ["параграф", "§"])


def test_marker_without_number_false():
    assert not has_para_marker_without_number("Безопасное поведение в горах", ["параграф", "§"])