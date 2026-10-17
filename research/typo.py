"""Fixes a mistyped syllable the table does not know (khogn -> khong), scored on clean and mistyped text.

usage: python -m research.typo MODEL.npz|TABLE.timsen TESTFILE...
Input is typed without marks, as for restore. A syllable is a fix target only when the table does not
know its unmarked form; candidates are the known forms one edit away (a letter replaced, removed,
added, or two neighbours swapped), ranked in context by the restore score. A fix is made when the best
candidate beats the runner-up (or keeping the word, as <unk>) by the margin. The clean pass counts
words that would be changed; the mistyped copy has one typo per sentence, drawn as below.
"""

import argparse
import random
import string

import numpy as np

from . import table
from .model import UNK, Model
from .spellcheck import local_score
from .text import segments, strip_marks

MARGINS = [0, 1, 2, 3, 4, 5, 6, 8]
ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
# Share of each kind of typo: a neighbouring key, two letters swapped, a letter left out, an extra key.
KINDS = [("near", 0.4), ("swap", 0.2), ("drop", 0.2), ("extra", 0.2)]


def neighbours():
    pos = {c: (r, i) for r, row in enumerate(ROWS) for i, c in enumerate(row)}
    near = {}
    for c, (r, i) in pos.items():
        near[c] = [d for d, (s, j) in pos.items() if d != c and abs(s - r) <= 1 and abs(j - i) <= 1]
    return near


NEAR = neighbours()


def edits(word):
    """Every string one edit away: replace, remove or add a letter, or swap two neighbours."""
    out = set()
    for i in range(len(word) + 1):
        a, b = word[:i], word[i:]
        if b:
            out.add(a + b[1:])
            out.update(a + c + b[1:] for c in string.ascii_lowercase)
        if len(b) > 1:
            out.add(a + b[1] + b[0] + b[2:])
        out.update(a + c + b for c in string.ascii_lowercase)
    out.discard(word)
    return out


def typo(word, rng):
    kind = rng.choices([k for k, _ in KINDS], weights=[w for _, w in KINDS])[0]
    i = rng.randrange(len(word))
    if kind == "near":
        return word[:i] + rng.choice(NEAR.get(word[i], [word[i]])) + word[i + 1 :]
    if kind == "swap" and i + 1 < len(word):
        return word[:i] + word[i + 1] + word[i] + word[i + 2 :]
    if kind == "drop":
        return word[:i] + word[i + 1 :]
    return word[:i] + rng.choice(NEAR.get(word[i], [word[i]]) + [word[i]]) + word[i:]


def known(m, plain):
    return bool(m.cand.get(plain)) or plain in m.id


def best_fix(m, plain_run, i):
    """(margin, fix) for the unknown syllable at i, or None when nothing known is one edit away."""
    cands = sorted(c for c in edits(plain_run[i]) if known(m, c))
    if not cands:
        return None
    restored = m.restore(plain_run)
    seq = np.array([m.id.get(w, UNK) for w in restored], dtype=np.int64)
    keep = local_score(m, seq, i, np.array([UNK]))[0]
    scores = np.array([local_score(m, seq, i, m.options(c)).max() for c in cands])
    order = np.argsort(-scores, kind="stable")
    runner = max(scores[order[1]] if len(cands) > 1 else -np.inf, keep)
    return scores[order[0]] - runner, cands[order[0]]


def evaluate(m, path):
    rng = random.Random(11)
    r = dict(words=0, unknown=0, typos=0, typo_known=0)
    changed, fixed, right = (np.zeros(len(MARGINS)) for _ in range(3))
    for line in open(path, encoding="utf-8"):
        for run in segments(line, tone_style=True):
            plain = [strip_marks(w) for w in run]
            r["words"] += len(plain)
            for i, p in enumerate(plain):
                if not known(m, p):
                    r["unknown"] += 1
                    f = best_fix(m, plain, i)
                    if f:
                        changed += np.array([f[0] >= t for t in MARGINS])
            spots = [i for i, p in enumerate(plain) if len(p) > 1 and known(m, p)]
            if not spots:
                continue
            i = rng.choice(spots)
            bad = typo(plain[i], rng)
            r["typos"] += 1
            if known(m, bad):
                r["typo_known"] += 1
                continue
            f = best_fix(m, plain[:i] + [bad] + plain[i + 1 :], i)
            if f:
                hit = np.array([f[0] >= t for t in MARGINS])
                fixed += hit
                right += hit & (f[1] == plain[i])
    return r, changed, fixed, right


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("tests", nargs="+")
    a = ap.parse_args()
    m = table.read(a.model) if a.model.endswith(".timsen") else Model(a.model)
    for test in a.tests:
        r, changed, fixed, right = evaluate(m, test)
        scored = r["typos"] - r["typo_known"]
        print(
            f"{test.rsplit('/', 1)[-1]}: {r['words']} clean words, {r['unknown']} unknown; "
            f"{r['typos']} typos, {r['typo_known']} landed on a known form, {scored} scored"
        )
        print("  margin  clean-changed  typo-fixed  fixed-right  right-of-fixed")
        for k, t in enumerate(MARGINS):
            print(
                f"  {t:6}  {changed[k] / r['words']:13.3%}  {fixed[k] / scored:10.1%}  "
                f"{right[k] / scored:11.1%}  {right[k] / max(fixed[k], 1):14.1%}",
                flush=True,
            )


if __name__ == "__main__":
    main()
