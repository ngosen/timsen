"""Counts syllable 1/2/3-grams from prepared corpora.

usage: python -m research.train OUT.npz CORPUS...

A corpus NAME reads every data/NAME*.txt.gz (one paragraph per line, held-out text already removed by
the fetch script). Words are mapped to the new tone placement before counting.
"""

import gzip
import sys
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np

from . import paths
from .model import BOS, EOS, SHIFT, UNK
from .text import segments

MIN_VOCAB = 3
MAX_VOCAB = (1 << SHIFT) - 1
CHUNK_LINES = 5_000  # small chunks keep each worker's arrays small
WORKERS = 8
MERGE_EVERY = 40


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
        for run in segments(text, tone_style=True):
            c.update(run)
    return c


VOCAB = None


def init_vocab(vocab):
    global VOCAB
    VOCAB = vocab


def count_ngrams(lines):
    seq = []
    get = VOCAB.get
    for text in lines:
        for run in segments(text, tone_style=True):
            seq += [BOS, BOS]
            seq += [get(w, UNK) for w in run]
            seq.append(EOS)
    a = np.array(seq, dtype=np.int64)
    uni = np.bincount(a, minlength=len(VOCAB) + 3)
    bk = ((a[:-1] << SHIFT) | a[1:])[a[1:] != BOS]
    tk = ((a[:-2] << (2 * SHIFT)) | (a[1:-1] << SHIFT) | a[2:])[(a[2:] != BOS) & (a[1:-1] != EOS)]
    return uni, np.unique(bk, return_counts=True), np.unique(tk, return_counts=True)


def merge(parts):
    keys = np.concatenate([p[0] for p in parts])
    counts = np.concatenate([p[1] for p in parts])
    uk, inv = np.unique(keys, return_inverse=True)
    return uk, np.bincount(inv, weights=counts).astype(np.int64)


def main():
    out, names = sys.argv[1], sys.argv[2:]
    t0 = time.time()
    with Pool(WORKERS) as pool:
        words = Counter()
        for c in pool.imap_unordered(count_words, chunks(names)):
            words.update(c)
    kept = [w for w, n in words.most_common(MAX_VOCAB - 3) if n >= MIN_VOCAB]
    vocab = {w: i + 3 for i, w in enumerate(kept)}
    print(f"tokens {sum(words.values()):,} vocab {len(vocab):,} ({time.time() - t0:.0f}s)", flush=True)
    uni = np.zeros(len(vocab) + 3, dtype=np.int64)
    bis, tris = [], []
    with Pool(WORKERS, initializer=init_vocab, initargs=(vocab,)) as pool:
        for u, b, t in pool.imap_unordered(count_ngrams, chunks(names)):
            uni += u
            bis.append(b)
            tris.append(t)
            if len(tris) >= MERGE_EVERY:
                bis, tris = [merge(bis)], [merge(tris)]
    bk, bc = merge(bis)
    tk, tc = merge(tris)
    print(f"bigrams {len(bk):,} trigrams {len(tk):,} ({time.time() - t0:.0f}s)", flush=True)
    np.savez(out, words=np.array(["<s>", "</s>", "<unk>", *kept]), uni=uni, bk=bk, bc=bc, tk=tk, tc=tc)


if __name__ == "__main__":
    main()
