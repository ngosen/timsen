import gzip
import sys

import pytest

from research import paths, prune, train
from research.model import SHIFT, Model

CORPUS = ["tôi gõ phím rất nhanh", "bàn phím này gõ rất êm", "tôi gõ bàn phím"] * 10


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


@pytest.mark.parametrize("seed", [None, 1])
def test_keeps_about_the_budget_and_every_trigram_context(model_path, seed):
    m = Model(model_path)
    full = len(m.bk) + len(m.tk)
    prune.select(m, full // 2, 0, seed)
    assert full // 2 <= len(m.bk) + len(m.tk) < full
    contexts = set(m.bk.tolist())
    for k in m.tk.tolist():
        u, v = k >> (2 * SHIFT), (k >> SHIFT) & ((1 << SHIFT) - 1)
        assert u == 0 and v == 0 or (u << SHIFT) | v in contexts


def test_writes_a_table_that_restores(model_path, tmp_path):
    m = Model(model_path)
    prune.select(m, (len(m.bk) + len(m.tk)) // 2, 0)
    out = tmp_path / "t.timsen"
    prune.table.write(m, out)
    assert prune.table.read(out).restore(["toi", "go", "phim"]) == ["tôi", "gõ", "phím"]
