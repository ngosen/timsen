import gzip
import sys

from research import paths, train
from research.coverage import coverage
from research.model import Model

CORPUS = ["tôi gõ phím rất nhanh", "bàn phím này gõ rất êm"] * 10


def test_counts_a_spelling_the_model_never_offers(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "DATA", tmp_path)
    with gzip.open(tmp_path / "tiny.txt.gz", "wt", encoding="utf-8") as f:
        f.write("\n".join(CORPUS) + "\n")
    out = tmp_path / "tiny.npz"
    monkeypatch.setattr(sys, "argv", ["train", str(out), "tiny"])
    monkeypatch.setattr(train, "WORKERS", 1)
    train.main()
    test = tmp_path / "test"
    # `gỗ` is not in the corpus, so `go` only offers `gõ`.
    test.write_text("tôi gõ phím\nbàn gỗ nhanh\n", encoding="utf-8")
    r = coverage(Model(out), test)
    assert r["words"] == 6
    assert r["covered"] == 5 / 6
    assert r["marked_covered"] == 4 / 5
