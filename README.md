# quiz-library

Библиотека викторины для голосовых навыков Алисы. Публичная, предмет-агностичная: «предмет → параграф → вопрос через LLM».

Берёт выжимки учебников (`digests/*.json`) и файл `subjects.json`, по строке домашнего задания находит номер параграфа, достаёт его блоки и генерирует один вопрос через LLM.

```

                    subjects.json + digests/
                          │
                          ▼
                    QuizService (эта библиотека)
                          │
        ┌─────────────────┼──────────────────────┐
        ▼                 ▼                      ▼
  DigestsRegistry   parse_paragraph()      LLMClient
  (выжимки →         (домашка → §N)        (вопрос по тексту)
   Paragraph)
```

---

## Установка

Python **3.11+**. Единственная зависимость — `aiohttp`.

```bash
pip install "quiz-library @ git+https://github.com/freeuser3/quiz-library.git"
# или из исходников:
pip install -e .
```

---

## Формат данных

Библиотека не содержит данных — она их читает (частями приватные, в git не хранятся).

### `subjects.json` — маппинг предметов

```json
{
  "География": {
    "book": "География. 9 класс",
    "digest": "digests/geografia.json",
    "paragraph_patterns": ["параграф", "параграфа", "§"]
  },
  "Биология": {
    "book": "Биология. 9 класс",
    "digest": "digests/biologia.json",
    "paragraph_patterns": ["параграф", "параграфа", "§"]
  }
}
```

- `digest` — путь к выжимке (относительно рабочей директории процесса);
- `paragraph_patterns` — паттерны для поиска номера параграфа в тексте
  (префиксы; длинные ставятся первыми: «параграфа» выигрывает у «параграф»);
- поиск предметов регистронезависим.

### `digests/*.json` — выжимка учебника

```json
{
  "meta": { "subject": "География", "title": "География. 9 класс", "source_pdf": "GEO.pdf" },
  "paragraphs": {
    "1": { "title": "Хозяйство России", "pages": { "start": 5, "end": 8 },
           "blocks": [{ "type": "text", "content": "…" }, { "type": "page", "no": 5 }] }
  }
}
```

`blocks` строит офлайн-пайплайн GeoRag: это страницы, текст, памятки, изображения
(`alt`/подписи), вопросы. Библиотека объединяет блоки параграфа в единую строку
для подачи в LLM.

---

## API

```python
from quiz_library.digests import load_registry
from quiz_library.service import QuizService
from quiz_library.llm import LLMClient, LLMConfig
from quiz_library.model import HomeworkEntry

llm = LLMClient(LLMConfig(base_url=..., api_key=..., model=..., timeout=20))
svc = QuizService.from_config("subjects.json", llm)

svc.patterns_for("География")                  # ['параграф', 'параграфа', '§']
svc.find_entry(entries, "Биология")            # запись домашки по предмету

q = await svc.question_for(entry)              # Question | None
```

`question_for` сам: распознаёт параграф → достаёт текст блоков → вызывает LLM → возвращает `Question(subject, paragraph, paragraph_title, pages, text)`. При ошибке LLM (`LLMError`) возвращает `None`, а не бросает исключение.

```python
r = load_registry("subjects.json")
r.subject("биология")                # регистронезависимо
r.paragraph("Биология", 6)           # Paragraph(number, title, pages, blocks) | None
```

Заметки:

- `paragraph_patterns` отсутствуют — `question_for` вернёт `None` для предмета;
- выжимка не найдена/битая — параграф не читается, `paragraph` даст `None`;
- LLM при генерации таймаутит по `LLMConfig.timeout`.

---

## Ошибки

| Ситуация | Поведение |
|----------|-----------|
| `llm.generate_question` не смог (сеть, таймаут, 5xx, не-строковый ответ) | `LLMError` → `question_for` возвращает `None` |
| Домашка не содержит номер параграфа | `None` |
| Выжимка повреждена / предмет отсутствует в `subjects.json` | `None` |

---

## Разработка и тесты

```bash
pip install -e ".[dev]"
pytest          # или GEO_DIGEST_PATH=... pytest для теста на реальной выжимке
```

Тесты используют фейковый LLM, реальная сеть не нужна. `GEO_DIGEST_PATH` (`env`)
указывает на частную выжимку географии для одного сквозного теста.

---

## Модульность

- **GeoRag** (офлайн-репозиторий) производит выжимки: «любой PDF с оглавлением → JSON».
- **quiz-library** (публичная) потребляет выжимки: «предмет → параграф → вопрос».
- **alice-homework** (навык) — только aliceio-обвязка вокруг quiz-library.

Изменение формата выжимок чинит GeoRag + quiz-library вместе и не трогает навык.

---

## Лицензия / приватность

Выжимки учебников и `subjects.json` — приватные данные, в этом репозитории их нет
(см. `.gitignore`). Публикуется только код.