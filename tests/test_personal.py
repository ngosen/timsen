import gzip
import sys

import pytest

from research import paths, personal, train
from research.model import SHIFT, Model

CORPUS = ["tôi gõ phím rất nhanh", "bàn phím này gõ rất êm"] * 10


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


def test_personal_counts_go_on_top_of_the_pruned_table(model_path):
    m = Model(model_path, min_tri=1000, min_bi=1000)
    assert len(m.tk) == len(m.bk) == 0
    personal.personalize(m, m.snapshot(), ["tôi gõ phím"], 1)
    toi, go, phim = (m.id[w] for w in ("tôi", "gõ", "phím"))
    key = (toi << (2 * SHIFT)) | (go << SHIFT) | phim
    assert len(m.tk) == 4  # BOS BOS tôi, BOS tôi gõ, tôi gõ phím, gõ phím EOS
    assert m.lookup(key, m.tk, m.tc) == 1


def test_main_prunes_the_base_table(model_path, tmp_path, monkeypatch, capsys):
    chat = tmp_path / "chat"
    chat.write_text("\n".join(CORPUS[:10]) + "\n", encoding="utf-8")
    seen = []

    class Spy(Model):
        def __init__(self, *args):
            seen.append(args[1:])
            super().__init__(*args)

    monkeypatch.setattr(personal, "Model", Spy)
    monkeypatch.setattr(sys, "argv", ["personal", str(model_path), str(chat), "1", "--min-tri", "7", "--min-bi", "3"])
    personal.main()
    assert seen == [(7, 3)]
    assert "weight 1 share 100%" in capsys.readouterr().out


def test_learn_scores_the_whole_chat_file_against_another_file(model_path, tmp_path, monkeypatch, capsys):
    chat, learned = tmp_path / "chat", tmp_path / "learned"
    chat.write_text("bàn phím này gõ rất êm\n", encoding="utf-8")
    learned.write_text("tôi gõ phím\n", encoding="utf-8")
    assert personal.splits(["a", "b"], ["c"]) == [(["a", "b"], ["c"])]
    monkeypatch.setattr(sys, "argv", ["personal", str(model_path), str(chat), "1", "--learn", str(learned)])
    personal.main()
    assert "(6 words)" in capsys.readouterr().out
