import gzip
import random
import sys

import pytest

from research import paths, train, typo
from research.model import Model

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


def test_edits_cover_each_kind_of_typo():
    e = typo.edits("phim")
    assert {"phm", "phiim", "phmi", "phin"} <= e
    assert "phim" not in e


def test_typos_stay_one_edit_away():
    rng = random.Random(1)
    for _ in range(200):
        assert typo.typo("nhanh", rng) in typo.edits("nhanh") | {"nhanh"}


def test_fixes_a_swapped_pair_in_context(model):
    margin, fix = typo.best_fix(model, ["toi", "go", "phmi", "rat"], 2)
    assert fix == "phim" and margin > 0


def test_no_fix_without_a_known_form_nearby(model):
    assert typo.best_fix(model, ["toi", "go", "xyzzy"], 2) is None


def test_labeled_scores_typos_and_real_words_apart(model, tmp_path):
    labels = tmp_path / "labels"
    labels.write_text("phmi\tphim\tvi\nzzz\t?\t-\n", encoding="utf-8")
    msgs = tmp_path / "msgs"
    msgs.write_text("toi go phmi rat nhanh\nban phim xyzzy\nzzz\n", encoding="utf-8")
    out = typo.labeled(model, msgs, typo.read_labels(labels))
    assert out["typo-vi"][0] == 1 and out["typo-vi"][2][0] == 1
    # xyzzy is a real word the table lacks; zzz is left out.
    assert out["real"][0] == 1 and out["real"][1][0] == 0
    assert set(out) == {"typo-vi", "real"}
