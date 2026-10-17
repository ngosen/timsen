import gzip
import sys

import numpy as np
import pytest

from research import model, paths, train
from research.model import EOS, FLOOR, SHIFT, Model

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


def triples(m):
    ids = np.arange(len(m.words))
    return np.meshgrid(ids, ids, ids, indexing="ij")


def test_pruning_raises_the_unkept_share(model_path):
    full, pruned = Model(model_path), Model(model_path, min_tri=11)
    assert np.all((full.left_bi >= np.log(FLOOR)) & (full.left_bi <= 0))
    # In the full model every continuation is a kept trigram; nothing follows a sentence end.
    ends = (full.bk & ((1 << SHIFT) - 1)) == EOS
    assert full.left_bi[~ends].max() == pytest.approx(np.log(FLOOR))
    assert pruned.left_bi.max() > np.log(0.5)


def test_backing_off_from_a_full_context_costs_more(model_path, monkeypatch):
    m = Model(model_path, min_tri=11)
    monkeypatch.setattr(model, "LEFTOVER", 0.0)
    plain = m.logp(*triples(m))
    monkeypatch.setattr(model, "LEFTOVER", 1.0)
    got = m.logp(*triples(m))
    assert np.all(got <= plain)
    assert np.any(got < plain - 1)
    # Scores of kept trigrams do not back off, so they do not change.
    u, v, w = m.tk >> (2 * SHIFT), (m.tk >> SHIFT) & ((1 << SHIFT) - 1), m.tk & ((1 << SHIFT) - 1)
    assert np.array_equal(got[u, v, w], plain[u, v, w])
