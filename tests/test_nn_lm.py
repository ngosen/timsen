import gzip
import sys

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from research import next_word, nn_lm, paths, train  # noqa: E402
from research.model import BOS, Model  # noqa: E402

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


def test_each_run_starts_with_bos(model):
    toi, go, phim = (model.id[w] for w in ("tôi", "gõ", "phím"))
    assert nn_lm.line_ids(model, "Tôi gõ, phím") == [BOS, toi, go, BOS, phim]


def test_scores_the_same_words_as_the_table(model, tmp_path):
    test = tmp_path / "test"
    test.write_text("tôi gõ phím rất nhanh\ntôi gõ, chữ\n", encoding="utf-8")
    lm = nn_lm.LM(len(model.words), 8, 16).eval()
    r = nn_lm.measure(model, lm, test, 3)
    t = next_word.measure(next_word.Suggester(model, 3), test)
    assert (r["words"], r["known"]) == (t["words"], t["known"]) == (8, 7)


def test_learns_what_follows(model, tmp_path, monkeypatch):
    data = tmp_path / "data.npy"
    np.save(data, np.concatenate([nn_lm.line_ids(model, line) for line in CORPUS * 5]).astype(np.int32))
    for name, value in [("LOG_EVERY", 100), ("BATCH", 16), ("SEQ", 16)]:
        monkeypatch.setattr(nn_lm, name, value)
    torch.manual_seed(0)
    out = tmp_path / "lm.pt"
    nn_lm.train(model, data, out, 0, 16, 32)
    test = tmp_path / "test"
    test.write_text("tôi gõ phím\n", encoding="utf-8")
    r = nn_lm.measure(model, nn_lm.load(model, out), test, 1)
    # gõ after tôi and phím after tôi gõ are certain in the corpus; the first word is not.
    assert r["top1"] >= 2
