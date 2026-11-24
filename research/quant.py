"""Scores a table with its counts rounded to a few bits each.

usage: python -m research.quant TABLE.timsen BITS TESTFILE... [--keep-leftover]

Counts are rounded in the log domain to 2**BITS levels (BITS 0 leaves them as the table holds them),
which is what a file storing a BITS-bit code per n-gram would hold. The leftover of each
context (Model.index_leftover) is then taken from the rounded counts; with --keep-leftover it stays
as the exact counts gave it, rounded to 256 levels, as a file storing it per bigram would.
"""

import argparse

import numpy as np

from . import table
from .evaluate import evaluate
from .model import FLOOR


def rounded(counts, bits, top):
    """counts rounded to the nearest of 2**bits levels spaced evenly in log between 1 and top."""
    if bits == 0:
        return counts
    step = np.log(top) / (2**bits - 1)
    return np.exp(np.rint(np.log(np.maximum(counts, 1)) / step) * step)


def rounded_leftover(left):
    step = -np.log(FLOOR) / 255
    return np.rint(left / step) * step


def quantize(m, bits, keep_leftover):
    exact = (m.left_bi, m.left_uni, m.left_bos)
    top = max(m.bc.max(), m.tc.max(), m.uni.max())
    m.bc, m.tc = rounded(m.bc, bits, top), rounded(m.tc, bits, top)
    m.index_leftover()
    if keep_leftover:
        m.left_bi, m.left_uni, m.left_bos = (rounded_leftover(a) for a in exact)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("table")
    ap.add_argument("bits", type=int)
    ap.add_argument("tests", nargs="+")
    ap.add_argument("--keep-leftover", action="store_true")
    a = ap.parse_args()
    m = table.read(a.table)
    quantize(m, a.bits, a.keep_leftover)
    print(
        f"{a.table}: bits {a.bits} keep-leftover {a.keep_leftover} bigrams {len(m.bk):,} trigrams {len(m.tk):,}",
        flush=True,
    )
    for test in a.tests:
        r = evaluate(m, test, m.restore)
        print(
            f"  {test.rsplit('/', 1)[-1]:12} words {r['words']:6} word {r['word']:.2%} sent {r['sent']:.2%}", flush=True
        )


if __name__ == "__main__":
    main()
