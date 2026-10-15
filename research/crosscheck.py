"""Writes the unmarked runs of a test file and how research.table restores them, for checking another
implementation word for word.

usage: python -m research.crosscheck TABLE.timsen TESTFILE RUNS EXPECTED
RUNS gets one unmarked run per line, EXPECTED the restored run on the same line.
"""

import sys

from . import table
from .text import segments, strip_marks


def runs(path):
    for line in open(path, encoding="utf-8"):
        for run in segments(line):
            yield [strip_marks(w) for w in run]


def write(table_path, test_path, runs_path, expected_path):
    m = table.read(table_path)
    with open(runs_path, "w", encoding="utf-8") as r, open(expected_path, "w", encoding="utf-8") as e:
        for plain in runs(test_path):
            r.write(" ".join(plain) + "\n")
            e.write(" ".join(m.restore(plain)) + "\n")


if __name__ == "__main__":
    write(*sys.argv[1:5])
