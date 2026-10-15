"""Writes the unmarked runs of a test file and how research.table restores them, for checking another
implementation word for word.

usage: python -m research.crosscheck TABLE.timsen TESTFILE RUNS EXPECTED [TRUTH]
RUNS gets one unmarked run per line, EXPECTED the restored run on the same line, and TRUTH the run as
written, with tone marks in the new placement (the table's), for scoring another implementation.
"""

import sys

from . import table
from .text import segments, strip_marks


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


if __name__ == "__main__":
    write(*sys.argv[1:6])
