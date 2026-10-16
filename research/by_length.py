"""Word and whole-run accuracy by run length (words between two punctuation marks).

usage: python -m research.by_length MODEL.npz TESTFILE
"""

import sys
from collections import defaultdict

from .model import Model
from .text import same, segments, strip_marks

BUCKETS = [(1, "1"), (2, "2"), (4, "3-4"), (8, "5-8"), (15, "9-15"), (10**9, "16+")]


def bucket(n):
    return next(name for top, name in BUCKETS if n <= top)


def main():
    m = Model(sys.argv[1])
    stats = defaultdict(lambda: [0, 0, 0, 0])  # words, right, runs, runs all right
    for line in open(sys.argv[2], encoding="utf-8"):
        for run in segments(line):
            hits = [same(t, g) for t, g in zip(run, m.restore([strip_marks(w) for w in run]))]
            s = stats[bucket(len(run))]
            s[0] += len(run)
            s[1] += sum(hits)
            s[2] += 1
            s[3] += len(hits) == len(run) and all(hits)
    print("length    words  word-right   runs  run-all-right")
    for _, name in BUCKETS:
        w, r, n, nr = stats[name]
        if n:
            print(f"{name:6} {w:8} {r / w:10.2%} {n:6} {nr / n:12.2%}")


if __name__ == "__main__":
    main()
