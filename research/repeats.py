"""Measures how often a sentence repeats one typed earlier, so it could be offered whole.

usage: python -m research.repeats SENTENCES [--prefix 2] [--start 0.8]
SENTENCES holds one sentence per line, oldest first (as research.chat_testset writes them). Lines from
the --start share onward are scored against every line before them. A completion counts when the
earlier sentence offered after the first --prefix words (the most frequent one, then the latest)
equals the sentence typed. Prints counts only, never sentences.
"""

import argparse
from collections import Counter, defaultdict

from .text import segments


def words(line):
    return tuple(w for run in segments(line, tone_style=True) for w in run)


def measure(lines, prefix, start):
    seen = Counter()
    by_prefix = defaultdict(Counter)
    last = {}
    r = dict(sents=0, repeat=0, long=0, offered=0, completed=0)
    for i, line in enumerate(lines):
        s = words(line)
        if i >= start and s:
            r["sents"] += 1
            r["repeat"] += seen[s] > 0
            if len(s) > prefix:
                r["long"] += 1
                past = by_prefix.get(s[:prefix])
                if past:
                    r["offered"] += 1
                    best = max(past, key=lambda c: (past[c], last[c]))
                    r["completed"] += best == s
        if s:
            seen[s] += 1
            by_prefix[s[:prefix]][s] += 1
            last[s] = i
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sentences")
    ap.add_argument("--prefix", type=int, default=2)
    ap.add_argument("--start", type=float, default=0.8)
    a = ap.parse_args()
    lines = open(a.sentences, encoding="utf-8").read().splitlines()
    r = measure(lines, a.prefix, int(len(lines) * a.start))
    n, n_long = max(r["sents"], 1), max(r["long"], 1)
    print(
        f"scored {r['sents']} sentences: repeat an earlier one {r['repeat'] / n:.2%}; "
        f"longer than {a.prefix} words {r['long']}, offered a completion {r['offered'] / n_long:.2%}, "
        f"completion right {r['completed'] / n_long:.2%}"
    )


if __name__ == "__main__":
    main()
