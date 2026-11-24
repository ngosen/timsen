"""Scores a table with its counts rounded to a few bits each, and sizes the file that would hold it.

usage: python -m research.quant TABLE.timsen BITS TESTFILE... [--keep-leftover]

Counts are rounded in the log domain to 2**BITS levels (BITS 0 leaves them exact), which is what a
file storing one small code per n-gram instead of a 32-bit count would hold. The leftover of each
context (Model.index_leftover) is then taken from the rounded counts; with --keep-leftover it stays
as the exact counts gave it, rounded to 256 levels, as a file storing it per bigram would.
"""

import argparse
import os

import numpy as np

from . import table
from .evaluate import evaluate
from .model import FLOOR

CHECKPOINT = 32  # bigrams per stored trigram offset in the sized layout


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


def dense_bytes(fixed, n_words, n_bi, n_tri, leftover):
    """File size with a 16-bit id and an 8-bit count code per n-gram, a one-byte trigram row length
    per bigram with an offset every CHECKPOINT bigrams, and optionally a leftover byte per bigram."""
    per_bigram = 2 + 1 + 1 + 4 / CHECKPOINT + (1 if leftover else 0)
    return int(fixed + 4 * (n_words + 1) + n_bi * per_bigram + n_tri * 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("table")
    ap.add_argument("bits", type=int)
    ap.add_argument("tests", nargs="+")
    ap.add_argument("--keep-leftover", action="store_true")
    a = ap.parse_args()
    m = table.read(a.table)
    n_bi, n_tri = len(m.bk), len(m.tk)
    fixed = os.path.getsize(a.table) - table.ngram_bytes(len(m.words), n_bi, n_tri)
    quantize(m, a.bits, a.keep_leftover)
    print(
        f"{a.table}: bits {a.bits} keep-leftover {a.keep_leftover} bigrams {n_bi:,} trigrams {n_tri:,} "
        f"dense {dense_bytes(fixed, len(m.words), n_bi, n_tri, a.keep_leftover) / 1e6:.2f} MB",
        flush=True,
    )
    for test in a.tests:
        r = evaluate(m, test, m.restore)
        print(
            f"  {test.rsplit('/', 1)[-1]:12} words {r['words']:6} word {r['word']:.2%} sent {r['sent']:.2%}", flush=True
        )


if __name__ == "__main__":
    main()
