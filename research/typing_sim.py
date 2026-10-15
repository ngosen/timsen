"""Accuracy under what an input method actually sees, and how often it could ask instead of guessing.

usage: python -m research.typing_sim MODEL.npz TESTFILE... [--margins 1,2,3,4,6]

- whole run: the restoration chosen after the last word of the run (what evaluate.py reports).
- left only: each word is fixed when typed, seeing only the words before it. An input method that
  never revises earlier words gets this accuracy.
- confidence: with the whole run restored, a word is "sure" when its spelling beats every other
  spelling of the same unmarked form by more than MARGIN (log score, neighbours fixed). The rest
  would be shown as a choice; "in top 3" says whether the right spelling is among the first three.
"""

import argparse

import numpy as np

from .model import UNK, Model
from .spellcheck import local_score
from .text import same, segments, strip_marks


def ranked(m, ids, i, plain):
    """Spellings of position i, best first, with their local scores, neighbours fixed."""
    cands = m.options(plain)
    if len(cands) < 2:
        return [m.word(cands[0], plain)], np.array([0.0])
    s = local_score(m, ids, i, cands)
    order = np.argsort(-s)
    return [m.word(cands[k], plain) for k in order], s[order]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("tests", nargs="+")
    ap.add_argument("--margins", default="1,2,3,4,6")
    a = ap.parse_args()
    margins = [float(x) for x in a.margins.split(",")]
    m = Model(a.model)
    for test in a.tests:
        words = whole = left = 0
        sure = np.zeros(len(margins))
        sure_right = np.zeros(len(margins))
        unsure_top3 = np.zeros(len(margins))
        for line in open(test, encoding="utf-8"):
            for run in segments(line):
                plain = [strip_marks(w) for w in run]
                got = m.restore(plain)
                online = [m.restore(plain[: i + 1])[-1] for i in range(len(plain))]
                ids = np.array([m.id.get(w, UNK) for w in got], dtype=np.int64)
                for i, truth in enumerate(run):
                    words += 1
                    whole += same(truth, got[i])
                    left += same(truth, online[i])
                    spellings, scores = ranked(m, ids, i, plain[i])
                    margin = scores[0] - scores[1] if len(scores) > 1 else np.inf
                    top3 = any(same(truth, s) for s in spellings[:3])
                    for k, t in enumerate(margins):
                        if margin > t:
                            sure[k] += 1
                            sure_right[k] += same(truth, got[i])
                        else:
                            unsure_top3[k] += top3
        name = test.rsplit("/", 1)[-1]
        print(f"{name}: {words} words  whole run {whole / words:.2%}  left only {left / words:.2%}")
        print("  margin  sure-share  right-when-sure  asked-share  right-in-top3-when-asked")
        for k, t in enumerate(margins):
            asked = words - sure[k]
            print(
                f"  {t:6}  {sure[k] / words:10.2%}  {sure_right[k] / max(sure[k], 1):15.2%}  "
                f"{asked / words:11.2%}  {unsure_top3[k] / max(asked, 1):24.2%}",
                flush=True,
            )


if __name__ == "__main__":
    main()
