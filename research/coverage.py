"""Share of words whose right spelling is among the candidates restore can pick: no change to scoring
can fix the rest.

usage: python -m research.coverage MODEL.npz|TABLE.timsen TESTFILE...
"""

import argparse

from . import table
from .model import Model
from .text import MARKED, same, segments, strip_marks


def coverage(m, path):
    words = covered = marked = marked_covered = 0
    for line in open(path, encoding="utf-8"):
        for run in segments(line):
            for truth in run:
                plain = strip_marks(truth)
                hit = any(same(truth, m.word(i, plain)) for i in m.options(plain))
                words += 1
                covered += hit
                if MARKED.search(truth):
                    marked += 1
                    marked_covered += hit
    return dict(words=words, covered=covered / words, marked_covered=marked_covered / max(marked, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("tests", nargs="+")
    a = ap.parse_args()
    m = table.read(a.model) if a.model.endswith(".timsen") else Model(a.model)
    for test in a.tests:
        r = coverage(m, test)
        print(
            f"{test.rsplit('/', 1)[-1]:12} words {r['words']:6} covered {r['covered']:.2%} "
            f"marked-covered {r['marked_covered']:.2%}",
            flush=True,
        )


if __name__ == "__main__":
    main()
