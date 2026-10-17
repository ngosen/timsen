"""Counts syllable 1/2/3-grams (and 4-grams with --order 4) from prepared corpora.

usage: python -m research.train [--order 4] [--breaks] OUT.npz CORPUS...

A corpus NAME reads every data/NAME*.txt.gz (one paragraph per line, held-out text already removed by
the fetch script). Words are mapped to the new tone placement before counting. With --breaks, runs go
on across commas, digits and symbols, which become one <p> word (see text.segments).
"""

import gzip
import sys
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np

from . import paths
from .model import BOS, EOS, SHIFT, UNK, quad_key
from .text import segments

MIN_VOCAB = 3
MAX_VOCAB = (1 << SHIFT) - 1
CHUNK_LINES = 5_000  # small chunks keep each worker's arrays small
WORKERS = 8
MERGE_EVERY = 40
MIN_QUAD = 2  # 4-grams seen once are most of the table and add little
ORDER = 3
BREAKS = False


def chunks(names):
    for name in names:
        files = sorted(paths.DATA.glob(f"{name}*.txt.gz"))
        if not files:
            sys.exit(f"no data/{name}*.txt.gz; run the matching fetch script first")
        for path in files:
            buf = []
            with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    buf.append(line)
                    if len(buf) >= CHUNK_LINES:
                        yield buf
                        buf = []
            if buf:
                yield buf


def count_words(lines):
    c = Counter()
    for text in lines:
        for run in segments(text, tone_style=True, breaks=BREAKS):
            c.update(run)
    return c


VOCAB = None


def init_vocab(vocab, order):
    global VOCAB, ORDER
    VOCAB, ORDER = vocab, order


def count_ngrams(lines):
    seq = []
    get = VOCAB.get
    for text in lines:
        for run in segments(text, tone_style=True, breaks=BREAKS):
            seq += [BOS, BOS]
            seq += [get(w, UNK) for w in run]
            seq.append(EOS)
    a = np.array(seq, dtype=np.int64)
    uni = np.bincount(a, minlength=len(VOCAB) + 3)
    bk = ((a[:-1] << SHIFT) | a[1:])[a[1:] != BOS]
    tk = ((a[:-2] << (2 * SHIFT)) | (a[1:-1] << SHIFT) | a[2:])[(a[2:] != BOS) & (a[1:-1] != EOS)]
    qk = np.zeros(0, dtype=np.uint64)
    if ORDER == 4:
        keep = (a[3:] != BOS) & (a[2:-1] != EOS) & (a[1:-2] != EOS) & (a[:-3] != EOS)
        qk = quad_key(a[:-3], a[1:-2], a[2:-1], a[3:])[keep]
    return uni, *(np.unique(k, return_counts=True) for k in (bk, tk, qk))


def merge(parts):
    keys = np.concatenate([p[0] for p in parts])
    counts = np.concatenate([p[1] for p in parts])
    uk, inv = np.unique(keys, return_inverse=True)
    return uk, np.bincount(inv, weights=counts).astype(np.int64)


def main():
    global ORDER, BREAKS
    args = sys.argv[1:]
    if args[0] == "--order":
        ORDER, args = int(args[1]), args[2:]
    BREAKS = args[0] == "--breaks"
    if BREAKS:
        args = args[1:]
    out, names = args[0], args[1:]
    t0 = time.time()
    with Pool(WORKERS) as pool:
        words = Counter()
        for c in pool.imap_unordered(count_words, chunks(names)):
            words.update(c)
    kept = [w for w, n in words.most_common(MAX_VOCAB - 3) if n >= MIN_VOCAB]
    vocab = {w: i + 3 for i, w in enumerate(kept)}
    print(f"tokens {sum(words.values()):,} vocab {len(vocab):,} ({time.time() - t0:.0f}s)", flush=True)
    uni = np.zeros(len(vocab) + 3, dtype=np.int64)
    parts = ([], [], [])
    with Pool(WORKERS, initializer=init_vocab, initargs=(vocab, ORDER)) as pool:
        for u, *grams in pool.imap_unordered(count_ngrams, chunks(names)):
            uni += u
            for part, g in zip(parts, grams):
                part.append(g)
            if len(parts[0]) >= MERGE_EVERY:
                parts = tuple([merge(p)] for p in parts)
    (bk, bc), (tk, tc), (qk, qc) = (merge(p) for p in parts)
    keep = qc >= MIN_QUAD
    qk, qc = qk[keep], qc[keep]
    print(f"bigrams {len(bk):,} trigrams {len(tk):,} 4-grams {len(qk):,} ({time.time() - t0:.0f}s)", flush=True)
    quads = {"qk": qk, "qc": qc} if ORDER == 4 else {}
    np.savez(out, words=np.array(["<s>", "</s>", "<unk>", *kept]), uni=uni, bk=bk, bc=bc, tk=tk, tc=tc, **quads)


if __name__ == "__main__":
    main()
