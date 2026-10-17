"""Strips marks from held-out sentences, restores them and scores the result.

usage: python -m research.evaluate MODEL.npz|TABLE.timsen TESTFILE... [--min-tri N] [--min-bi N]
       [--backoff X] [--leftover GAMMA] [--breaks]
Test files hold one sentence per line. hoà/hòa count as the same word. With --breaks, runs go on
across commas, digits and symbols (see text.segments), for a model trained with --breaks; the
<p> they become is not scored.
"""

import argparse

import numpy as np

from . import model as model_mod
from . import table
from .model import Model
from .text import BREAK, MARKED, same, segments, strip_marks


def evaluate(model, path, restore, breaks=False):
    words = right = sents = sents_right = marked = marked_right = plain = plain_changed = 0
    for line in open(path, encoding="utf-8"):
        ok = True
        for run in segments(line, breaks=breaks):
            got = restore([strip_marks(w) for w in run])
            # zip would score only the words returned, so a shortened run would look right.
            if len(got) != len(run):
                raise ValueError(f"restore returned {len(got)} words for {len(run)}")
            for truth, g in zip(run, got):
                if truth == BREAK:
                    continue
                hit = same(truth, g)
                words += 1
                right += hit
                ok &= hit
                if MARKED.search(truth):
                    marked += 1
                    marked_right += hit
                else:
                    plain += 1
                    plain_changed += not hit
        sents += 1
        sents_right += ok
    return dict(
        sents=sents,
        words=words,
        word=right / words,
        sent=sents_right / sents,
        marked_right=marked_right / max(marked, 1),
        plain_changed=plain_changed / max(plain, 1),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("tests", nargs="+")
    ap.add_argument("--min-tri", type=int, default=1)
    ap.add_argument("--min-bi", type=int, default=1)
    ap.add_argument("--backoff", type=float, default=0.4, help="weight of each step down to a shorter n-gram")
    ap.add_argument("--leftover", type=float, default=0.5, help="see Model.index_leftover; 0 is plain backoff")
    ap.add_argument("--breaks", action="store_true")
    a = ap.parse_args()
    model_mod.BACKOFF = np.log(a.backoff)
    model_mod.LEFTOVER = a.leftover
    m = table.read(a.model) if a.model.endswith(".timsen") else Model(a.model, a.min_tri, a.min_bi)
    print(
        f"{a.model}: vocab {len(m.words):,} bigrams {len(m.bk):,} trigrams {len(m.tk):,} "
        f"({m.entries * 12 / 1e6:.0f} MB at 12 B/entry)",
        flush=True,
    )
    for test in a.tests:
        r = evaluate(m, test, m.restore, a.breaks)
        print(
            f"  {test.rsplit('/', 1)[-1]:12} sents {r['sents']:5} words {r['words']:6} word {r['word']:.2%} "
            f"sent {r['sent']:.2%} marked-right {r['marked_right']:.2%} plain-changed {r['plain_changed']:.2%}",
            flush=True,
        )


if __name__ == "__main__":
    main()
