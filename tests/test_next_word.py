import gzip
import sys

import pytest

from research import next_word, paths, train
from research.model import BOS, EOS, UNK, Model

CORPUS = ["tôi gõ phím rất nhanh", "bàn phím này gõ rất êm"] * 10


@pytest.fixture
def model(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "DATA", tmp_path)
    with gzip.open(tmp_path / "tiny.txt.gz", "wt", encoding="utf-8") as f:
        f.write("\n".join(CORPUS) + "\n")
    out = tmp_path / "tiny.npz"
    monkeypatch.setattr(sys, "argv", ["train", str(out), "tiny"])
    monkeypatch.setattr(train, "WORKERS", 1)
    train.main()
    return Model(out)


def test_suggests_the_word_seen_after_the_context(model):
    s = next_word.Suggester(model, 3)
    toi, go, phim = (model.id[w] for w in ("tôi", "gõ", "phím"))
    assert s.suggest(toi, go)[0] == phim


def test_never_suggests_markers(model):
    s = next_word.Suggester(model, 50)
    rat, nhanh = model.id["rất"], model.id["nhanh"]
    top = s.suggest(rat, nhanh).tolist()
    assert top and not {BOS, EOS, UNK} & set(top)


def test_unknown_words_are_never_hits(model, tmp_path):
    test = tmp_path / "test"
    test.write_text("tôi gõ phím rất nhanh\ntôi gõ chữ\n", encoding="utf-8")
    r = next_word.measure(next_word.Suggester(model, 3), test)
    assert r["words"] == 8 and r["known"] == 7
    assert r["topk"] == 7
    # tôi gõ, gõ phím, phím rất, rất nhanh are suggested as pairs; gõ chữ is not.
    assert r["pairs"] == 6 and r["pair"] == 5
