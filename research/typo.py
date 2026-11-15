"""Fixes a mistyped syllable the table does not know (khogn -> khong), scored on clean and mistyped text.

usage: python -m research.typo MODEL.npz|TABLE.timsen TESTFILE... [--typing]
       python -m research.typo MODEL.npz|TABLE.timsen MESSAGES... --labels LABELS [--typing]
       python -m research.typo TABLE.timsen TESTFILE... --write-fixes OUT
Input is typed without marks, as for restore. A syllable is a fix target only when the table does not
know its unmarked form; candidates are the known forms one edit away (a letter replaced, removed,
added, or two neighbours swapped), ranked in context by the restore score. A fix is made when the best
candidate beats the runner-up (or keeping the word, as <unk>) by the margin. The clean pass counts
words that would be changed; the mistyped copy has one typo per sentence, drawn as below.
--typing decides each syllable when its word ends, as an input method does: only the words before it
are context, and the run is not over. --write-fixes writes every fix decision, both ways, on the
clean runs and their mistyped copies, for checking another implementation (see write_fixes).
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


def best_fix(m, plain_run, i, ended=True):
    """(margin, fix) for the unknown syllable at i, or None when nothing known is one edit away."""
    cands = sorted(c for c in edits(plain_run[i]) if known(m, c))
    if not cands:
        return None
    restored = m.restore(plain_run, ended)
    seq = np.array([m.id.get(w, UNK) for w in restored], dtype=np.int64)
    keep = local_score(m, seq, i, np.array([UNK]), ended)[0]
    scores = np.array([local_score(m, seq, i, m.options(c), ended).max() for c in cands])
    order = np.argsort(-scores, kind="stable")
    runner = max(scores[order[1]] if len(cands) > 1 else -np.inf, keep)
    return scores[order[0]] - runner, cands[order[0]]


def fix_at(m, plain_run, i, typing):
    """best_fix for the syllable at i, seen when its word ends (typing) or with the whole run."""
    return best_fix(m, plain_run[: i + 1], i, ended=False) if typing else best_fix(m, plain_run, i)


def write_fixes(m, runs, out):
    """RUN, I, MODE, FIX, MARGIN per unknown syllable of each run, MODE ended or typing; - for no fix."""
    for run in runs:
        plain = [w.lower() for w in run]
        for i, p in enumerate(plain):
            if known(m, p):
                continue
            for typing in (False, True):
                fix = fix_at(m, plain, i, typing)
                margin, best = (repr(float(fix[0])), fix[1]) if fix else ("-", "-")
                mode = "typing" if typing else "ended"
                out.write(f"{' '.join(run)}\t{i}\t{mode}\t{best}\t{margin}\n")


def clean_and_mistyped(path):
    """Each unmarked run of a test file, then the same run with one typo, drawn as evaluate draws them
    but in any syllable of two letters or more, so the runs do not depend on the table."""
    rng = random.Random(11)
    for line in open(path, encoding="utf-8"):
        for run in segments(line, tone_style=True):
            plain = [strip_marks(w) for w in run]
            yield plain
            spots = [i for i, p in enumerate(plain) if len(p) > 1]
            if spots:
                i = rng.choice(spots)
                yield plain[:i] + [typo(plain[i], rng)] + plain[i + 1 :]


def evaluate(m, path, typing=False):
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
                    f = fix_at(m, plain, i, typing)
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
            f = fix_at(m, plain[:i] + [bad] + plain[i + 1 :], i, typing)
            if f:
                hit = np.array([f[0] >= t for t in MARGINS])
                fixed += hit
                right += hit & (f[1] == plain[i])
    return r, changed, fixed, right


def read_labels(path):
    """FORM, INTENDED, KIND per line, tab-separated. INTENDED is the unmarked form meant, ! for a typo
    with no single intended word, ? to leave the form out. Forms not listed are real words."""
    labels = {}
    for line in open(path, encoding="utf-8"):
        form, intended, kind = line.rstrip("\n").split("\t")
        labels[form] = (intended, kind)
    return labels


def labeled(m, path, labels, typing=False):
    """For each kind of unknown word: occurrences, and per margin how many were changed and changed right."""
    out = {}
    for line in open(path, encoding="utf-8"):
        for run in segments(line, tone_style=True):
            plain = [strip_marks(w) for w in run]
            for i, p in enumerate(plain):
                if known(m, p):
                    continue
                intended, kind = labels.get(p, (None, "real"))
                if intended == "?":
                    continue
                if intended is not None:
                    kind = f"typo-{kind}"
                n, changed, right = out.setdefault(kind, [0, np.zeros(len(MARGINS)), np.zeros(len(MARGINS))])
                out[kind][0] = n + 1
                f = fix_at(m, plain, i, typing)
                if f:
                    hit = np.array([f[0] >= t for t in MARGINS])
                    changed += hit
                    right += hit & (f[1] == intended)
    return out


def print_labeled(out):
    for kind, (n, changed, right) in sorted(out.items()):
        print(f"{kind}: {n} occurrences")
        print("  margin  changed  changed-right")
        for k, t in enumerate(MARGINS):
            print(f"  {t:6}  {int(changed[k]):7}  {int(right[k]):13}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("tests", nargs="+")
    ap.add_argument("--labels", help="score the unknown words of message files against these labels")
    ap.add_argument("--typing", action="store_true", help="decide each syllable when its word ends")
    ap.add_argument("--write-fixes", help="write every fix decision to this file instead of scoring")
    a = ap.parse_args()
    m = table.read(a.model) if a.model.endswith(".timsen") else Model(a.model)
    if a.write_fixes:
        with open(a.write_fixes, "w", encoding="utf-8") as out:
            for test in a.tests:
                write_fixes(m, clean_and_mistyped(test), out)
        return
    if a.labels:
        labels = read_labels(a.labels)
        for test in a.tests:
            print_labeled(labeled(m, test, labels, a.typing))
        return
    for test in a.tests:
        r, changed, fixed, right = evaluate(m, test, a.typing)
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
