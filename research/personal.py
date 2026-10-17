"""Adds counts from the user's own text to a base model (the personal dictionary), scored 5-fold.

usage: python -m research.personal MODEL.npz|TABLE.timsen CHATFILE WEIGHT... [--fractions 0,0.1,1]
       [--min-tri N] [--min-bi N] [--backoff X] [--leftover GAMMA]
Each fold is a contiguous fifth of the file, so sentences from one message rarely land on both sides.
With --fractions, each fold trains on that share of the other four fifths (sampled with a fixed seed).
--min-tri and --min-bi prune the base table before personal counts are added, as a shipped table would be.
"""

import argparse
import random

import numpy as np

from . import model as model_mod
from . import table
from .model import BOS, EOS, SHIFT, UNK, Model
from .text import same, segments, strip_marks

FOLDS = 5


def counts(model, lines):
    seq = []
    for line in lines:
        for run in segments(line, tone_style=True):
            seq += [BOS, BOS, *[model.id.get(w, UNK) for w in run], EOS]
    a = np.array(seq, dtype=np.int64)
    uni = np.bincount(a, minlength=len(model.words)).astype(np.float64)
    bk = ((a[:-1] << SHIFT) | a[1:])[a[1:] != BOS]
    tk = ((a[:-2] << (2 * SHIFT)) | (a[1:-1] << SHIFT) | a[2:])[(a[2:] != BOS) & (a[1:-1] != EOS)]
    return uni, np.unique(bk, return_counts=True), np.unique(tk, return_counts=True)


def add(keys, cnts, extra, weight):
    k = np.concatenate([keys, extra[0]])
    c = np.concatenate([cnts, extra[1] * weight])
    uk, inv = np.unique(k, return_inverse=True)
    return uk, np.bincount(inv, weights=c)


def personalize(m, base, lines, weight):
    m.restore_snapshot(base)
    if not lines:
        return
    uni, b, t = counts(m, lines)
    m.uni = base[0] + weight * uni
    m.nseg = base[5] + weight * uni[EOS]
    m.uni[BOS] = m.nseg
    # On top of the base total: a table file's total also counts words it left out.
    m.total = base[6] + weight * (uni[3:].sum() + uni[EOS])
    m.bk, m.bc = add(base[1], base[2], b, weight)
    m.tk, m.tc = add(base[3], base[4], t, weight)


def score(m, lines):
    words = right = 0
    for line in lines:
        for run in segments(line):
            got = m.restore([strip_marks(w) for w in run])
            words += len(run)
            right += sum(same(a, b) for a, b in zip(run, got))
    return words, right


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("chat")
    ap.add_argument("weights", nargs="+", type=float)
    ap.add_argument("--fractions", default="1")
    ap.add_argument("--min-tri", type=int, default=1)
    ap.add_argument("--min-bi", type=int, default=1)
    ap.add_argument("--backoff", type=float, default=0.4)
    ap.add_argument("--leftover", type=float, default=0.5, help="see Model.index_leftover; 0 is plain backoff")
    a = ap.parse_args()
    model_mod.BACKOFF = np.log(a.backoff)
    model_mod.LEFTOVER = a.leftover
    lines = open(a.chat, encoding="utf-8").read().splitlines()
    size = len(lines) // FOLDS + 1
    m = table.read(a.model) if a.model.endswith(".timsen") else Model(a.model, a.min_tri, a.min_bi)
    base = m.snapshot()
    for weight in a.weights:
        for frac in (float(x) for x in a.fractions.split(",")):
            rng = random.Random(3)
            words = right = 0
            for f in range(FOLDS):
                test = lines[f * size : (f + 1) * size]
                train = lines[: f * size] + lines[(f + 1) * size :]
                personalize(m, base, rng.sample(train, int(len(train) * frac)), weight)
                w, r = score(m, test)
                words += w
                right += r
            print(f"weight {weight:g} share {frac:.0%}: word {right / words:.2%} ({words} words)", flush=True)


if __name__ == "__main__":
    main()
