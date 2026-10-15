"""Writes the unmarked runs of a test file and how research.table restores them, for checking another
implementation word for word.

usage: python -m research.crosscheck TABLE.timsen TESTFILE RUNS EXPECTED [TRUTH]
       python -m research.crosscheck --personal TABLE.timsen TEXT RUNS LEARNED EXPECTED
RUNS gets one unmarked run per line, EXPECTED the restored run on the same line, and TRUTH the run as
written, with tone marks in the new placement (the table's), for scoring another implementation.
With --personal, the table first learns the lines of TEXT whose words it knows, as research.personal
does with weight WEIGHT; LEARNED gets their runs, one per line, for the other implementation to learn.
RUNS must already exist.
"""

import sys

from . import personal, table
from .text import segments, strip_marks

WEIGHT = 100


def runs(path):
    """Each run as written (new tone placement) and unmarked."""
    for line in open(path, encoding="utf-8"):
        for run in segments(line, tone_style=True):
            yield run, [strip_marks(w) for w in run]


def write(table_path, test_path, runs_path, expected_path, truth_path=None):
    m = table.read(table_path)
    truth = open(truth_path, "w", encoding="utf-8") if truth_path else None
    with open(runs_path, "w", encoding="utf-8") as r, open(expected_path, "w", encoding="utf-8") as e:
        for written, plain in runs(test_path):
            r.write(" ".join(plain) + "\n")
            e.write(" ".join(m.restore(plain)) + "\n")
            if truth:
                truth.write(" ".join(written) + "\n")
    if truth:
        truth.close()


def write_personal(table_path, text_path, runs_path, learned_path, expected_path):
    m = table.read(table_path)
    # Words the table lacks become <unk> here but new words in the crate, so leave those lines out.
    lines = [
        line
        for line in open(text_path, encoding="utf-8").read().splitlines()
        if all(w in m.id for run in segments(line, tone_style=True) for w in run)
    ]
    personal.personalize(m, m.snapshot(), lines, WEIGHT)
    with open(learned_path, "w", encoding="utf-8") as f:
        for line in lines:
            for run in segments(line, tone_style=True):
                f.write(" ".join(run) + "\n")
    with open(expected_path, "w", encoding="utf-8") as e:
        for run in open(runs_path, encoding="utf-8").read().splitlines():
            e.write(" ".join(m.restore(run.split(" "))) + "\n")


if __name__ == "__main__":
    if sys.argv[1] == "--personal":
        write_personal(*sys.argv[2:7])
    else:
        write(*sys.argv[1:6])
