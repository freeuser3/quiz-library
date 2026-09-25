from quiz_library.match import normalize_title, tokenize, title_similarity, search_paragraphs


def test_normalize_lower_strip_punct():
    assert normalize_title("Тема 1. Общие представления о ЗДОРОВЬЕ!") == "общие представления о здоровье"
    assert normalize_title("Модуль 7. Безопасность. Среда…") == "безопасность среда"


def test_normalize_strips_module_and_topic_leader():
    assert normalize_title("Модуль 9. Тема 4. Правила безопасного поведения при угрозе наводнения и цунами") == \
        "правила безопасного поведения при угрозе наводнения и цунами"


def test_tokenize_returns_prefix_classes():
    assert tokenize("Безопасное поведение в горах!") == ["безо", "пове", "в", "гора"]


def test_tokenize_unifies_inflections_and_ocr_noise():
    assert tokenize("безопасность в горах") == tokenize("безорасного в гора")


def test_title_similarity_is_coverage_of_query():
    assert title_similarity(["безо", "в", "цифр", "сред"], ["безо", "в", "цифр", "сред"]) == 1.0
    assert title_similarity(["безо", "в", "цифр", "сред"], ["безо", "в", "цифр"]) == 0.75
    assert title_similarity(["безо", "в", "цифр", "сред"], ["цифр"]) == 0.25


def test_search_hills_query_finds_gora_topic_first():
    titles = [
        ("1.2", "Модуль 1. Тема 2. Правила вызова экстренных служб"),
        ("5.4", "Модуль 5. Тема 4. Правила безопасного поведения в горах"),
        ("2.1", "Модуль 2. Тема 1. Здоровье и как его сохранить"),
    ]
    got = search_paragraphs(titles, "Безопасное поведение в горах", threshold=0.3)
    assert got[0][0] == "5.4"


def test_search_water_query_finds_water_topic():
    titles = [
        ("5.4", "Модуль 5. Тема 4. Правила безопасного поведения в горах"),
        ("5.5", "Модуль 5. Тема 5. Правила безопасного поведения на водоёмах"),
    ]
    got = search_paragraphs(titles, "Правила безопасного поведения на водоёмах", threshold=0.3)
    assert got[0][0] == "5.5"


def test_search_natural_environment_prefers_module5_over_digital():
    titles = [
        ("5.4", "Модуль 5. Тема 4. Правила безопасного поведения в горах"),
        ("5.5", "Модуль 5. Тема 5. Правила безопасного поведения на водоёмах"),
        ("5.1", "Модуль 5. Тема 1. Классификация чрезвычайных ситуаций природного характера"),
        ("8.1", "Модуль 8. Тема 1. Безопасность в цифровой среде"),
    ]
    got = search_paragraphs(titles, "Правила безопасного поведения в природной среде", threshold=0.3)
    assert got[0][0] == "5.4"


def test_search_fire_natural_tie_includes_fire_topics():
    titles = [
        ("8.1", "Модуль 8. Тема 1. Безопасность в цифровой среде"),
        ("2.4", "Модуль 2. Тема 4. Пожарная безопасность в жилых помещениях"),
        ("4.3", "Модуль 4. Тема 3. Пожарная безопасность и безопасное поведение при пожаре"),
    ]
    got = search_paragraphs(titles, "Пожарная безопасность в природной среде", threshold=0.3)
    assert any(k in ("2.4", "4.3") for k, _, _ in got[:2])


def test_search_manipulation_finds_single_topic():
    titles = [
        ("7.3", "Модуль 7. Тема 3. Манипулирование и способы противостоять ему"),
        ("5.2", "Модуль 5. Тема 2. Правила безопасного поведения при химических авариях"),
        ("7.4", "Модуль 7. Тема 4. Основы противодействия экстремизму и терроризму"),
    ]
    got = search_paragraphs(titles, "Манипуляция и способы противостоять ей", threshold=0.3)
    assert got and got[0][0] == "7.3"