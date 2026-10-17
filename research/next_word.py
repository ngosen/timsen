"""Measures next-word suggestions: how often the word typed next is among the model's top K.

usage: python -m research.next_word MODEL.npz|TABLE.timsen TESTFILE... [--k 3] [--learn FILE --weight W]
The context is the two words before, as already typed with marks; a run starts after punctuation, as in
restore. A pair counts when one of the K suggested pairs (each first word with its best next word)
equals the next two words. With --learn, FILE's counts are added first as a personal dictionary.
"""

import argparse

import numpy as np

from . import table
from .model import BOS, EOS, SHIFT, UNK, Model
from .personal import personalize
from .text import segments

MASK = (1 << SHIFT) - 1
# Bigram-only words are ranked by their bigram count, so the most frequent few are enough.
TOP_BI = 200


def followers(keys, counts, prefix):
    """Ids that follow a packed context in an ascending key array, with their counts."""
    lo, hi = np.searchsorted(keys, [prefix << SHIFT, (prefix + 1) << SHIFT])
    return keys[lo:hi] & MASK, counts[lo:hi]


class Suggester:
    def __init__(self, m, k):
        self.m, self.k = m, k
        uni = m.uni.copy()
        uni[[BOS, EOS, UNK]] = 0
        self.top_uni = np.argsort(-uni, kind="stable")[:k]

    def suggest(self, u, v, k=None):
        """The k most likely next words after (u, v), best first."""
        m, k = self.m, k or self.k
        tri, _ = followers(m.tk, m.tc, (u << SHIFT) | v)
        bi, bc = followers(m.bk, m.bc, v)
        bi = bi[np.argsort(-bc, kind="stable")[:TOP_BI]]
        cand = np.unique(np.concatenate([tri, bi, self.top_uni]))
        cand = cand[(cand != BOS) & (cand != EOS) & (cand != UNK)]
        score = m.logp(u, v, cand)
        return cand[np.argsort(-score, kind="stable")[:k]]


def measure(s, path):
    m = s.m
    r = dict(words=0, known=0, top1=0, topk=0, pairs=0, pair=0)
    for line in open(path, encoding="utf-8"):
        for run in segments(line, tone_style=True):
            ids = [m.id.get(w, UNK) for w in run]
            ctx = [BOS, BOS, *ids]
            for i, w in enumerate(ids):
                u, v = ctx[i], ctx[i + 1]
                top = s.suggest(u, v)
                r["words"] += 1
                r["known"] += w != UNK
                r["top1"] += len(top) > 0 and top[0] == w and w != UNK
                r["topk"] += w != UNK and w in top
                if i + 1 < len(ids):
                    r["pairs"] += 1
                    nxt = ids[i + 1]
                    if w != UNK and nxt != UNK and w in top:
                        r["pair"] += s.suggest(v, w, 1)[:1].tolist() == [nxt]
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("tests", nargs="+")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--learn")
    ap.add_argument("--weight", type=float, default=1000.0)
    a = ap.parse_args()
    m = table.read(a.model) if a.model.endswith(".timsen") else Model(a.model)
    if a.learn:
        lines = open(a.learn, encoding="utf-8").read().splitlines()
        personalize(m, m.snapshot(), lines, a.weight)
    s = Suggester(m, a.k)
    for test in a.tests:
        r = measure(s, test)
        n, p = r["words"], max(r["pairs"], 1)
        print(
            f"{test.rsplit('/', 1)[-1]:12} words {n:6} in-vocab {r['known'] / n:.2%} top1 {r['top1'] / n:.2%} "
            f"top{a.k} {r['topk'] / n:.2%} pair-in-top{a.k} {r['pair'] / p:.2%} ({r['pairs']} pairs)",
            flush=True,
        )


if __name__ == "__main__":
    main()
