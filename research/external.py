"""Scores another program's restoration of a test file, on the same words as research.evaluate.

usage: python -m research.external strip TESTFILE [--runs] > INPUT
       python -m research.external score TESTFILE RESTORED [--runs]
strip writes each sentence without marks, lowercased, punctuation and spacing kept; the other
program restores INPUT line by line into RESTORED. With --runs, INPUT holds one run per line
instead (see text.segments), which is the context research.evaluate gives a model.
"""

import argparse

from .evaluate import evaluate
from .text import TOKEN, WORD, normalize, same, segments, strip_marks


def stripped(line):
    return TOKEN.sub(lambda m: strip_marks(m[0]) if WORD.match(m[0]) else m[0], normalize(line.rstrip("\n")))


def strip(path, runs):
    for line in open(path, encoding="utf-8"):
        if runs:
            for run in segments(line):
                print(" ".join(strip_marks(w) for w in run))
        else:
            print(stripped(line))


def score_runs(path, restored):
    """evaluate() with the other program's lines as the restore function, one line per run."""
    lines = iter(open(restored, encoding="utf-8"))
    result = evaluate(None, path, lambda run: normalize(next(lines)).split())
    if next(lines, None) is not None:
        raise ValueError("more restored lines than runs")
    return result


def score_sentences(path, restored):
    words = right = sents = sents_right = 0
    truths, gots = open(path, encoding="utf-8"), open(restored, encoding="utf-8")
    for truth, got in zip(truths, gots, strict=True):
        want, have = TOKEN.findall(normalize(truth)), TOKEN.findall(normalize(got))
        # A restorer that merges or splits tokens would shift every later word against the truth.
        if len(want) != len(have):
            raise ValueError(f"sentence {sents + 1}: {len(have)} tokens restored for {len(want)}")
        ok = True
        for t, g in zip(want, have):
            if WORD.match(t):
                hit = same(t, g)
                words += 1
                right += hit
                ok &= hit
        sents += 1
        sents_right += ok
    return dict(sents=sents, words=words, word=right / words, sent=sents_right / sents)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["strip", "score"])
    ap.add_argument("test")
    ap.add_argument("restored", nargs="?")
    ap.add_argument("--runs", action="store_true")
    a = ap.parse_args()
    if a.command == "strip":
        strip(a.test, a.runs)
        return
    if not a.restored:
        ap.error("score needs RESTORED")
    r = (score_runs if a.runs else score_sentences)(a.test, a.restored)
    print(
        f"{a.restored}: {a.test.rsplit('/', 1)[-1]} sents {r['sents']} words {r['words']} "
        f"word {r['word']:.2%} sent {r['sent']:.2%}"
    )


if __name__ == "__main__":
    main()
