import gzip
import sys

import pytest

from research import evaluate, paths, train
from research.model import Model
from research.text import BREAK

CORPUS = [
    "tôi gõ phím rất nhanh",
    "bàn phím này gõ rất êm",
    "gỗ lim làm bàn rất bền",
    "cái bàn bằng gỗ lim",
] * 10


@pytest.fixture
def model_path(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "DATA", tmp_path)
    with gzip.open(tmp_path / "tiny.txt.gz", "wt", encoding="utf-8") as f:
        f.write("\n".join(CORPUS) + "\n")
    out = tmp_path / "tiny.npz"
    monkeypatch.setattr(sys, "argv", ["train", str(out), "tiny"])
    monkeypatch.setattr(train, "WORKERS", 1)
    train.main()
    return out


def test_restore_uses_context_to_pick_the_spelling(model_path):
    m = Model(model_path)
    assert m.restore(["toi", "go", "phim"]) == ["tôi", "gõ", "phím"]
    assert m.restore(["ban", "bang", "go", "lim"]) == ["bàn", "bằng", "gỗ", "lim"]


def test_unknown_words_are_left_alone(model_path):
    m = Model(model_path)
    assert m.restore(["toi", "commit", "code"]) == ["tôi", "commit", "code"]


def test_evaluate_scores_a_held_out_file(model_path, tmp_path):
    test = tmp_path / "held-out"
    test.write_text("tôi gõ phím\ncái bàn bằng gỗ\n", encoding="utf-8")
    m = Model(model_path)
    r = evaluate.evaluate(m, test, m.restore)
    assert r["words"] == 7
    assert r["word"] == 1.0


# "mà" outnumbers "má", so only the word before the comma can pick má.
BREAK_CORPUS = ["con mèo, mà về"] * 10 + ["ba, má về"] * 5


@pytest.mark.parametrize("breaks", [False, True])
def test_breaks_keep_the_word_before_a_comma_as_context(tmp_path, monkeypatch, breaks):
    monkeypatch.setattr(paths, "DATA", tmp_path)
    with gzip.open(tmp_path / "br.txt.gz", "wt", encoding="utf-8") as f:
        f.write("\n".join(BREAK_CORPUS) + "\n")
    out = tmp_path / "br.npz"
    monkeypatch.setattr(sys, "argv", ["train", *(["--breaks"] if breaks else []), str(out), "br"])
    monkeypatch.setattr(train, "WORKERS", 1)
    train.main()
    m = Model(out)
    if breaks:
        assert m.restore(["ba", BREAK, "ma", "ve"]) == ["ba", BREAK, "má", "về"]
    else:
        assert m.restore(["ma", "ve"])[0] == "mà"
    test = tmp_path / "held-out"
    test.write_text("ba, má về\n", encoding="utf-8")
    r = evaluate.evaluate(m, test, m.restore, breaks)
    assert r["words"] == 3
    assert r["word"] == (1.0 if breaks else 2 / 3)


# "ta có gõ" outnumbers "ta có gỗ", so only the word before "ta" can pick gỗ.
FOUR_GRAM_CORPUS = ["nhà ta có gỗ"] * 5 + ["người ta có gõ"] * 10


@pytest.mark.parametrize(("order", "expected"), [(3, "gõ"), (4, "gỗ")])
def test_fourth_word_back_decides_when_the_trigram_cannot(tmp_path, monkeypatch, order, expected):
    monkeypatch.setattr(paths, "DATA", tmp_path)
    with gzip.open(tmp_path / "quad.txt.gz", "wt", encoding="utf-8") as f:
        f.write("\n".join(FOUR_GRAM_CORPUS) + "\n")
    out = tmp_path / "quad.npz"
    monkeypatch.setattr(sys, "argv", ["train", "--order", str(order), str(out), "quad"])
    monkeypatch.setattr(train, "WORKERS", 1)
    train.main()
    m = Model(out)
    assert m.restore(["nha", "ta", "co", "go"]) == ["nhà", "ta", "có", expected]
    assert m.restore(["nguoi", "ta", "co", "go"]) == ["người", "ta", "có", "gõ"]
