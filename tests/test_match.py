from quiz_library.match import normalize_title, tokenize, rare_terms, title_similarity, search_paragraphs


def test_normalize_lower_and_strip_punct():
    assert normalize_title("Тема 1. Общие представления о ЗДОРОВЬЕ!") == "общие представления о здоровье"
    assert normalize_title("Модуль 7. Безопасность. Среда…") == "безопасность среда"


def test_normalize_keeps_digit_and_strip_leader():
    assert normalize_title("Безопасное поведение в горах") == "безопасное поведение в горах"


def test_tokenize_words_only():
    assert tokenize("Безопасное поведение в горах!") == ["безопасное", "поведение", "в", "горах"]


def test_rare_terms_freq_lt_2():
    titles = ["безопасное поведение в горах", "безопасное поведение в лесу", "пожарная безопасность"]
    # безопасное=2 поведение=2 в=2 — НЕ редкие; горах=1 лесу=1 пожарная=1 безопасность=1 — редкие
    assert rare_terms(titles) == {"горах", "лесу", "пожарная", "безопасность"}


def test_пожарная_query_returns_correct_topic_first():
    titles = [("7.5", "Безопасное поведение и современные увлечения молодёжи"),
              ("8.1", "Безопасность в цифровой среде"),
              ("5.3", "Пожарная безопасность в природной среде"),
              ("5.1", "Правила безопасного поведения в природной среде")]
    got = search_paragraphs(titles, "Пожарная безопасность в природной среде")
    assert got[0][0] == "5.3"
