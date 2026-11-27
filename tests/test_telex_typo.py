import gzip
import random
import sys

import numpy as np
import pytest

from research import paths, train
from research import telex_typo as tt
from research.model import UNK, Model

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
    monkeypatch.setattr(tt, "COMMON", 1)
    return Model(out)


@pytest.fixture
def driver(tmp_path):
    """A stand-in core: it shows the keys as typed, and knows the words near two key strings."""
    path = tmp_path / "driver"
    path.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        "near = {'phin': 'phím=n,nn phin=e', 'xyzzy': ''}\n"
        "for line in sys.stdin:\n"
        "    keys = line.strip()\n"
        "    print(keys + '\\t' + near.get(keys, '') if len(sys.argv) > 1 else keys)\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return [str(path)]


def test_neighbours_follow_the_stagger_of_the_rows():
    assert all(b in tt.NEAR[a] and a in tt.NEAR[b] for a, b in ["mn", "bn", "df", "op", "aq", "sx"])
    assert "e" not in tt.NEAR["a"] and "c" not in tt.NEAR["s"] and "a" not in tt.NEAR["a"]


def test_each_kind_of_slip_changes_the_keys_its_own_way():
    rng = random.Random(3)
    keys = "nguowif"
    for _ in range(100):
        assert (
            len(tt.slip(keys, rng, "near"))
            == len(keys)
            != sum(a == b for a, b in zip(tt.slip(keys, rng, "near"), keys))
        )
        assert sorted(tt.slip(keys, rng, "swap")) == sorted(keys)
        assert len(tt.slip(keys, rng, "beside")) == len(tt.slip(keys, rng, "twice")) == len(keys) + 1
        assert len(tt.slip(keys, rng, "drop")) == len(keys) - 1
        assert tt.slip(keys, rng, "shape") == "nguooif"
    assert tt.slip("nguooif", rng, "shape") == "nguowif"


def test_a_mistyped_word_differs_from_its_keys():
    rng = random.Random(5)
    drawn = [tt.mistype("tieengs", rng) for _ in range(300)]
    assert all(bad != "tieengs" for bad, _ in drawn)
    assert {kind for _, kind in drawn} == {*tt.KINDS, "two"}


def test_reads_a_line_of_the_driver():
    shown, words = tt.read_near("nguồi\tngười=f,s hòa=nn hoà=n\n".rstrip("\n"))
    assert shown == "nguồi"
    assert words == {"người": ["f", "s"], "hoà": ["nn", "n"]}
    assert tt.read_near("khogn\t") == ("khogn", {})


def test_the_cheapest_way_to_a_word_counts():
    assert tt.units(["f", "s"]) == 1
    assert tt.units(["nn", "e"]) == 2
    assert tt.units(["f"]) == 2.5


def test_the_driver_answers_in_order(driver):
    assert tt.through(driver, ["b", "a", "c"]) == ["b", "a", "c"]
    assert tt.through(driver, []) == []


def test_fixes_a_slip_in_context_and_a_cost_can_stop_it(model):
    left = [model.id["tôi"], model.id["gõ"]]
    cands = tt.nearby_words(model, "phin", {"phím": ["n"]}, 0)
    stay, rated = tt.rate(model, left, UNK, cands)
    margin, word = tt.choose(stay, rated, 0)
    assert word == "phím" and margin > 0
    assert tt.choose(stay, rated, 100)[0] < 0 < margin
    assert tt.choose(stay, [], 0) is None


def test_a_word_the_table_knows_is_no_target_until_it_counts_as_rare(model):
    assert tt.nearby_words(model, "phím", {"nhanh": ["f"]}, 0) == {}
    assert set(tt.nearby_words(model, "phím", {"nhanh": ["f"]}, 10**6)) == {"nhanh"}
    assert tt.nearby_words(model, "phin", {"zzz": ["n"]}, 0) == {}


def test_judges_clean_and_mistyped_words_apart(model, driver, tmp_path):
    test = tmp_path / "test"
    test.write_text("tôi gõ phím\n", encoding="utf-8")
    cases = [c for c in tt.cases_of(test, plain=True) if c[3] is None]
    truth = cases[0][0]
    cases += [(truth, 2, "phin", "near"), (truth, 2, "xyzzy", "far"), (truth, 2, "phim", "drop")]
    out, kinds, counts = tt.judge(model, cases, tt.read_nearby(model, driver, cases, 0), 0, plain=True)
    clean, bad = out[0]
    assert (clean.n, clean.made[0]) == (3, 0)
    assert counts == dict(absorbed=1, known=0, reachable=1)
    assert (bad.n, bad.made[0], bad.right[0]) == (2, 1, 1)
    assert kinds[0, "near"].right[0] == 1 and kinds[0, "far"].made[0] == 0
    # phin is one letter from phim, so today's fix reaches it too; it has nothing for xyzzy either.
    assert np.array_equal(out["today"][1].made, out["today"][1].right) and out["today"][1].right[0] == 1


def test_shows_the_fix_of_keys_typed_after_some_words(model, driver, capsys):
    tt.show(model, driver, ["tôi", "gõ"], ["phin", "xyzzy"], 0)
    first, second = capsys.readouterr().out.splitlines()
    assert first.startswith("phin -> phin: phím +")
    assert second == "xyzzy -> xyzzy: "


def test_lists_the_words_typed_right_that_the_fix_changes(model, driver):
    truth = ["tôi", "gõ", "phin"]
    cases = [(truth, i, w, None) for i, w in enumerate(["tooi", "gox", "phin"])] + [(truth, 2, "phin", "near")]
    nearby = {"tooi": ("tôi", {}), "gox": ("gõ", {}), "phin": ("phin", {"phím": ["n"]})}
    (was, now, won), *rest = tt.changed(model, cases, nearby, 0, 0, 0, False)
    assert (was, now, rest) == ("phin", "phím", []) and won > 0
    assert list(tt.changed(model, cases, nearby, 0, won + 1, 0, False)) == []
    assert [(a, b) for a, b, _ in tt.changed(model, cases, nearby, None, 0, 0, False)] == [("phin", "phím")]
