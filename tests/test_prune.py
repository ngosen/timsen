import gzip
import sys

import pytest

from research import fixture, paths, prune, train
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


def test_a_byte_budget_bounds_the_file(model_path, tmp_path):
    full = Model(model_path)
    out = tmp_path / "full.timsen"
    prune.table.write(full, out)
    budget = out.stat().st_size - 50
    m = Model(model_path)
    prune.select(m, None, 0, max_bytes=budget)
    small = tmp_path / "small.timsen"
    prune.table.write(m, small)
    assert budget - 100 < small.stat().st_size <= budget


def test_n_grams_of_equal_weight_do_not_push_the_file_over_the_budget(tmp_path, monkeypatch):
    # Hundreds of continuations of one pair of words, each seen as often as the others.
    monkeypatch.setattr(paths, "DATA", tmp_path)
    with gzip.open(tmp_path / "long.txt.gz", "wt", encoding="utf-8") as f:
        f.write("\n".join(fixture.long_corpus()) + "\n")
    path = tmp_path / "long.npz"
    monkeypatch.setattr(sys, "argv", ["train", str(path), "long"])
    monkeypatch.setattr(train, "WORKERS", 1)
    train.main()
    full, out = tmp_path / "full.timsen", tmp_path / "t.timsen"
    prune.table.write(Model(path), full)
    sizes = set()
    empty = Model(path)
    prune.select(empty, 0, 0)
    prune.table.write(empty, out)
    for budget in range(out.stat().st_size + 80, full.stat().st_size, 500):
        m = Model(path)
        prune.select(m, None, 0, max_bytes=budget)
        prune.table.write(m, out)
        assert out.stat().st_size <= budget
        sizes.add(out.stat().st_size)
    assert len(sizes) > 2


def test_a_budget_with_no_room_for_n_grams_keeps_none(model_path, tmp_path):
    m = Model(model_path)
    prune.select(m, 0, 0)
    assert len(m.bk) == len(m.tk) == 0
    out = tmp_path / "empty.timsen"
    prune.table.write(m, out)
    empty = out.stat().st_size
    assert prune.table.read(out).restore(["toi", "go"]) == ["tôi", "gõ"]
    # The size is estimated with every section padded in full, so a few bytes more are needed.
    m = Model(model_path)
    prune.select(m, None, 0, max_bytes=empty + 80)
    prune.table.write(m, out)
    assert out.stat().st_size <= empty + 80
    with pytest.raises(ValueError):
        prune.select(Model(model_path), None, 0, max_bytes=empty - 1)


def test_min_candidate_leaves_rare_spellings_out_of_the_table(model_path, tmp_path, monkeypatch):
    out = tmp_path / "t.timsen"
    argv = ["prune", str(model_path), str(out), "--bytes", "100000", "--min-candidate", "15"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(prune.model_mod, "MIN_CANDIDATE", prune.model_mod.MIN_CANDIDATE)
    prune.main()
    # `êm` is seen 10 times, `gõ` 30.
    assert prune.table.read(out).restore(["go", "rat", "em"]) == ["gõ", "rất", "em"]
