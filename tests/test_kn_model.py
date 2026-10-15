import math

import numpy as np
import pytest

from research import kn_model

# log10 probabilities; the bigram "gõ phím" exists, "gỗ phím" backs off through gỗ's backoff weight.
ARPA = """\\data\\
ngram 1=7
ngram 2=3

\\1-grams:
-1.0\t<unk>\t0
-99\t<s>\t-0.5
-1.0\t</s>\t0
-1.0\tgõ\t-0.2
-1.2\tgỗ\t-0.3
-1.0\tphím\t0
-1.5\tlim\t0

\\2-grams:
-0.1\t<s> gõ\t0
-0.2\tgõ phím\t0
-0.01\tgỗ lim\t0

\\end\\
"""


@pytest.fixture
def model(tmp_path):
    arpa = tmp_path / "m.arpa"
    arpa.write_text(ARPA, encoding="utf-8")
    kn_model.convert(arpa, tmp_path / "m.npz")
    cand = tmp_path / "cand.npz"
    words = np.array(["<s>", "</s>", "<unk>", "gõ", "gỗ", "phím", "lim"])
    np.savez(cand, words=words, uni=np.array([0, 0, 0, 9, 9, 9, 9]))
    return kn_model.KNModel(tmp_path / "m.npz", cand)


def test_known_bigram_uses_its_own_probability(model):
    hist = np.array([[model.id["gõ"]]])
    assert model.logp(hist, np.array([model.id["phím"]]))[0] == pytest.approx(-0.2 * math.log(10))


def test_unseen_bigram_backs_off_through_the_context(model):
    hist = np.array([[model.id["gỗ"]]])
    expected = (-0.3 + -1.0) * math.log(10)
    assert model.logp(hist, np.array([model.id["phím"]]))[0] == pytest.approx(expected)


def test_restore_picks_the_spelling_the_context_supports(model):
    assert model.restore(["go", "phim"]) == ["gõ", "phím"]
    assert model.restore(["go", "lim"]) == ["gỗ", "lim"]
