import json

import pytest

from quiz_library.digests import load_subjects, load_registry, DigestsRegistry, SubjectEntry
from quiz_library.model import Paragraph


def _write_subjects(tmp_path, digest_path):
    subjects = {
        "География": {
            "book": "Алексеев. География 9 класс",
            "digest": str(digest_path),
            "paragraph_patterns": ["параграф", "параграфа", "§"],
        },
        "биология": {
            "book": "учебник",
            "digest": str(digest_path),
            "paragraph_patterns": ["параграф"],
        },
    }
    p = tmp_path / "subjects.json"
    p.write_text(json.dumps(subjects, ensure_ascii=False), encoding="utf-8")
    return p


def _write_digest(path):
    digest = {
        "meta": {"subject": "География", "title": "География. 9 класс"},
        "paragraphs": {
            "6": {
                "title": "Газовая промышленность",
                "pages": {"start": 22, "end": 25},
                "blocks": [
                    {"type": "page", "no": 22},
                    {"type": "text", "lines": ["Природный газ.", "Газ горит."]},
                ],
            }
        },
    }
    path.write_text(json.dumps(digest, ensure_ascii=False), encoding="utf-8")


def test_load_subjects_returns_entries(tmp_path):
    dg = tmp_path / "g.json"
    _write_digest(dg)
    subjects_path = _write_subjects(tmp_path, dg)
    raw = load_subjects(subjects_path)
    assert "География" in raw
    assert raw["География"]["digest"] == str(dg)


def test_subject_case_insensitive(tmp_path):
    dg = tmp_path / "g.json"
    _write_digest(dg)
    r = load_registry(_write_subjects(tmp_path, dg))
    assert r.subject("география") is not None
    assert r.subject("БИОЛОГия") is not None
    assert r.subject("НетТаких") is None


def test_paragraph_loaded(tmp_path):
    dg = tmp_path / "g.json"
    _write_digest(dg)
    r = load_registry(_write_subjects(tmp_path, dg))
    p = r.paragraph("География", 6)
    assert isinstance(p, Paragraph)
    assert p.title == "Газовая промышленность"
    assert p.pages == (22, 25)
    assert p.blocks[0]["type"] == "page"


def test_paragraph_missing_returns_none(tmp_path):
    dg = tmp_path / "g.json"
    _write_digest(dg)
    r = load_registry(_write_subjects(tmp_path, dg))
    assert r.paragraph("География", 999) is None
    assert r.paragraph("НетТаких", 6) is None


def test_digest_file_missing_returns_none(tmp_path):
    subjects_path = _write_subjects(tmp_path, tmp_path / "missing.json")
    r = load_registry(subjects_path)
    assert r.paragraph("География", 6) is None


def test_registry_on_real_geography_digest(geo_digest_path):
    import tempfile
    import os
    # реальная выжимка GeoRag (env GEO_DIGEST_PATH), §6 известен из интеграции
    with tempfile.TemporaryDirectory() as td:
        sp = os.path.join(td, "subjects.json")
        with open(sp, "w", encoding="utf-8") as f:
            json.dump({"География": {
                "book": "Алексеев. География 9 класс",
                "digest": geo_digest_path,
                "paragraph_patterns": ["параграф", "параграфа", "§"],
            }}, f, ensure_ascii=False)
        r = load_registry(sp)
        p = r.paragraph("География", 6)
        assert p is not None
        assert p.title
        assert p.pages == (22, 25)
        assert any(b["type"] == "questions" for b in p.blocks)