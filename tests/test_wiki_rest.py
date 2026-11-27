import sys

import pytest

from research import paths, wiki_rest

ARTICLES = [
    (7, "Hà Nội là thủ đô. Ừ. Sông Hồng chảy qua thành phố"),
    (8, "Bài này không được giữ lại"),
    (1007, "Huế nằm bên sông Hương\nĐà Nẵng nằm bên sông Hàn"),
]
HELD_OUT = [
    "Hà Nội là thủ đô",
    "Sông Hồng chảy qua thành phố",
    "Huế nằm bên sông Hương",
    "Đà Nẵng nằm bên sông Hàn",
]


def test_takes_the_usable_sentences_of_held_out_articles_in_order():
    assert wiki_rest.held_out(ARTICLES) == HELD_OUT


def set_up(root, monkeypatch, known):
    monkeypatch.setattr(paths, "TEST", root)
    monkeypatch.setattr(paths, "ensure", lambda: None)
    monkeypatch.setattr(wiki_rest, "TEST_SENTENCES", 2)
    monkeypatch.setattr(wiki_rest, "articles", lambda: ARTICLES)
    (root / "wiki").write_text("\n".join(known) + "\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["wiki_rest", str(root / "rest")])


def test_writes_the_sentences_after_the_test_set(tmp_path, monkeypatch):
    set_up(tmp_path, monkeypatch, HELD_OUT[:2])
    wiki_rest.main()
    assert (tmp_path / "rest").read_text(encoding="utf-8").splitlines() == HELD_OUT[2:]


def test_stops_when_the_dump_is_not_the_one_the_test_set_came_from(tmp_path, monkeypatch):
    set_up(tmp_path, monkeypatch, [HELD_OUT[0], "một câu khác hẳn"])
    with pytest.raises(SystemExit):
        wiki_rest.main()
    assert not (tmp_path / "rest").exists()
