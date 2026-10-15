import gzip
import sys

import pytest

from research import paths, table, train
from research.model import Model

# "gỗ" ends up below the candidate threshold, so the table drops it and the n-grams that use it.
CORPUS = ["tôi gõ phím rất nhanh", "bàn phím này gõ rất êm", "cái bàn bằng gỗ lim"] * 4
RUNS = [
    ["toi", "go", "phim"],
    ["ban", "bang", "go", "lim"],
    ["phim", "nay", "rat", "em"],
    ["toi", "commit", "code"],
    ["lim"],
]


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


@pytest.mark.parametrize(("min_tri", "min_bi"), [(1, 1), (5, 1), (5, 5)])
def test_table_restores_exactly_like_the_pruned_model(model_path, tmp_path, min_tri, min_bi):
    m = Model(model_path, min_tri, min_bi)
    table.write(m, tmp_path / "t.timsen")
    t = table.read(tmp_path / "t.timsen")
    assert t.total == m.total
    for run in RUNS:
        assert t.restore(run) == m.restore(run)
        for w in [*run, "<unk>"]:
            ids = m.options(w)
            assert [t.words[i] for i in t.options(w)] == [m.words[i] for i in ids]
            assert (t.logp(t.options(w), t.options(w), t.options(w)) == m.logp(ids, ids, ids)).all()


def test_table_drops_words_restore_never_picks(model_path, tmp_path):
    m = Model(model_path)
    table.write(m, tmp_path / "t.timsen")
    t = table.read(tmp_path / "t.timsen")
    assert "gỗ" in m.words and "gỗ" not in t.words
    assert len(t.bk) < len(m.bk) and len(t.tk) < len(m.tk)
