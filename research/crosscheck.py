"""Writes the unmarked runs of a test file and how research.table restores them, for checking another
implementation word for word.

usage: python -m research.crosscheck TABLE.timsen TESTFILE RUNS EXPECTED [TRUTH]
       python -m research.crosscheck --personal TABLE.timsen TEXT RUNS LEARNED EXPECTED
       python -m research.crosscheck --lines TESTFILE OUT
RUNS gets one unmarked run per line, EXPECTED the restored run on the same line, and TRUTH the run as
written, with tone marks in the new placement (the table's), for scoring another implementation.
With --personal, the table first learns the lines of TEXT whose words it knows, as research.personal
does with its auto weight; LEARNED gets their runs, one per line, for the other implementation to learn.
RUNS must already exist. With --lines, OUT keeps the lines of TESTFILE, each as its runs separated by
tabs, every run written twice: as written (new tone placement), then unmarked.
"""

import sys

from . import personal, table
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


def write_lines(test_path, out_path):
    with open(out_path, "w", encoding="utf-8") as out:
        for line in open(test_path, encoding="utf-8"):
            runs = segments(line, tone_style=True)
            out.write("\t".join(f"{' '.join(r)}\t{' '.join(strip_marks(w) for w in r)}" for r in runs) + "\n")


def write_personal(table_path, text_path, runs_path, learned_path, expected_path):
    m = table.read(table_path)
    # Words the table lacks become <unk> here but new words in the crate, so leave those lines out.
    lines = [
        line
        for line in open(text_path, encoding="utf-8").read().splitlines()
        if all(w in m.id for run in segments(line, tone_style=True) for w in run)
    ]
    personal.personalize(m, m.snapshot(), lines, None)
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
    elif sys.argv[1] == "--lines":
        write_lines(*sys.argv[2:4])
    else:
        write(*sys.argv[1:6])
