"""Flags marked words whose context prefers another word with the same unmarked form (gỗ phím -> gõ).

usage: python -m research.spellcheck MODEL.npz TESTFILE... [--weighted] [--min-tri N] [--min-bi N]

A clean pass over each test sentence counts false alarms. A copy with one word swapped for another
word of the same unmarked form counts how often that word is flagged and fixed back. --weighted draws
the swapped-in word by corpus frequency, which looks like real typos; the default (uniform) also
produces rare forms that are easy to catch and overstate recall.
"""

import argparse
import random

import numpy as np

from .model import BOS, EOS, UNK, Model
from .text import same, segments, strip_marks

MARGINS = [0, 1, 2, 3, 4, 5, 6, 8]


def local_score(m, seq, i, cands, ended=True):
    """Sum of every trigram score that involves position i, for each candidate placed there. With
    ended=False the run may still go on, so the end of the run is not scored."""
    pad = np.concatenate([[BOS, BOS], seq, [EOS] if ended else []]).astype(np.int64)
    j = i + 2
    total = np.zeros(len(cands))
    for k in range(j, min(j + 3, len(pad))):
        cols = [np.full(len(cands), x, dtype=np.int64) for x in pad[k - 2 : k + 1]]
        cols[2 - (k - j)] = cands
        total += m.logp(*cols)
    return total


def check(m, run):
    """Per word: (margin by which the best other spelling beats it, that spelling), or None."""
    seq = np.array([m.id.get(w, UNK) for w in run], dtype=np.int64)
    out = []
    for i, w in enumerate(run):
        cands = m.options(strip_marks(w))
        if len(cands) < 2 or seq[i] == UNK or not (cands == seq[i]).any():
            out.append(None)
            continue
        others = np.array([c != seq[i] and not same(m.words[c], w) for c in cands])
        if not others.any():
            out.append(None)
            continue
        s = local_score(m, seq, i, cands)
        best = np.argmax(np.where(others, s, -np.inf))
        out.append((s[best] - s[cands == seq[i]][0], m.words[cands[best]]))
    return out


def corrupt(m, run, rng, weighted):
    spots = []
    for i, w in enumerate(run):
        if w in m.id:
            alts = [m.words[c] for c in m.options(strip_marks(w)) if not same(m.words[c], w)]
            if alts:
                spots.append((i, alts))
    if not spots:
        return None
    i, alts = rng.choice(spots)
    new = list(run)
    new[i] = rng.choices(alts, weights=[m.uni[m.id[x]] for x in alts])[0] if weighted else rng.choice(alts)
    return new, i, run[i]


def evaluate(m, path, weighted):
    rng = random.Random(7)
    clean = injected = 0
    alarms, caught, fixed = (np.zeros(len(MARGINS)) for _ in range(3))
    for line in open(path, encoding="utf-8"):
        for run in segments(line, tone_style=True):
            for r in check(m, run):
                clean += 1
                if r:
                    alarms += np.array([r[0] > t for t in MARGINS])
            bad = corrupt(m, run, rng, weighted)
            if not bad:
                continue
            new, i, truth = bad
            injected += 1
            r = check(m, new)[i]
            if r:
                hit = np.array([r[0] > t for t in MARGINS])
                caught += hit
                fixed += hit & same(r[1], truth)
    return clean, alarms, injected, caught, fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("tests", nargs="+")
    ap.add_argument("--weighted", action="store_true")
    ap.add_argument("--min-tri", type=int, default=1)
    ap.add_argument("--min-bi", type=int, default=1)
    a = ap.parse_args()
    m = Model(a.model, a.min_tri, a.min_bi)
    print(f"{a.model}, errors {'by frequency' if a.weighted else 'uniform'}")
    for test in a.tests:
        n, alarms, inj, caught, fixed = evaluate(m, test, a.weighted)
        print(f"  {test.rsplit('/', 1)[-1]}: {n} clean words, {inj} injected errors")
        print("    margin  false-alarm  caught  fixed-right")
        for k, t in enumerate(MARGINS):
            print(f"    {t:6}  {alarms[k] / n:10.2%}  {caught[k] / inj:6.1%}  {fixed[k] / inj:10.1%}", flush=True)


if __name__ == "__main__":
    main()
