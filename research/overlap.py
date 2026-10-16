"""Finds test sentences that also occur in training text, and splits each test set by it.

usage: python -m research.overlap OUT_DIR
A test sentence counts when it equals a whole training line or one of its sentences (split as the
fetch scripts split them), whitespace collapsed. Writes OUT_DIR/SET.found and OUT_DIR/SET.clean for
each test set and prints counts per training corpus; it never prints sentences.
"""

import gzip
import sys
from multiprocessing import Pool
from pathlib import Path

from . import paths
from .text import SENTENCE_END

SETS = ["wiki", "subs", "web", "forum"]
CORPORA = ["wiki", "subs", "web", "forum-1", "forum-2", "forum-3", "forum-4"]


def key(text):
    return " ".join(text.split())


def test_index():
    """For each test set, its sentences mapped to the line numbers they occupy."""
    index = {}
    for s in SETS:
        index[s] = {}
        for i, line in enumerate((paths.TEST / s).read_text(encoding="utf-8").splitlines()):
            index[s].setdefault(key(line), []).append(i)
    return index


def scan(corpus):
    index = test_index()
    found = {s: set() for s in SETS}
    with gzip.open(paths.DATA / f"{corpus}.txt.gz", "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            for piece in [line, *SENTENCE_END.split(line)]:
                k = key(piece)
                for s in SETS:
                    found[s].update(index[s].get(k, ()))
    return corpus, found


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    with Pool(len(CORPORA)) as pool:
        results = pool.map(scan, CORPORA)
    union = {s: set() for s in SETS}
    for corpus, found in results:
        print(corpus, " ".join(f"{s} {len(found[s])}" for s in SETS))
        for s in SETS:
            union[s] |= found[s]
    for s in SETS:
        lines = (paths.TEST / s).read_text(encoding="utf-8").splitlines()
        with open(out / f"{s}.found", "w", encoding="utf-8") as a, open(out / f"{s}.clean", "w", encoding="utf-8") as b:
            for i, line in enumerate(lines):
                (a if i in union[s] else b).write(line + "\n")
        print(f"{s}: {len(union[s])} found, {len(lines) - len(union[s])} clean")


if __name__ == "__main__":
    main()
