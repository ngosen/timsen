"""Writes a table that keeps the n-grams whose removal would change scores the most, instead of the
most frequent ones, at a fixed number of n-grams or file size.

usage: python -m research.prune MODEL.npz OUT.timsen --entries N|--bytes N [--min-plain N] [--random SEED]

An n-gram's weight is its count times how far its own log score is from the score restore would use
without it (the next shorter n-gram, with the backoff penalty), after Stolcke (1998). A bigram that is
the context of a kept trigram is always kept, since the trigram's score divides by its count.
--bytes keeps as many n-grams as fit in a file of that size. --random keeps the same number of
n-grams chosen at random, to show the weights matter.
"""

import argparse

import numpy as np

from . import model as model_mod
from . import table
from .model import BOS, EOS, SHIFT, UNK, Model

MASK = np.int64((1 << SHIFT) - 1)


def kept_words(m, min_plain):
    opts = table.options_table(m, min_plain)
    keep = np.zeros(len(m.words), dtype=bool)
    keep[[BOS, EOS, UNK, *(i for ids in opts.values() for i in ids)]] = True
    return keep


def trigram_weights(m):
    u, v, w = m.tk >> (2 * SHIFT), (m.tk >> SHIFT) & MASK, m.tk & MASK
    ctx = m.lookup((u << SHIFT) | v, m.bk, m.bc)
    ctx = np.where((u == BOS) & (v == BOS), m.nseg, ctx)
    own = np.log(m.tc / np.maximum(ctx, 1))
    bi = m.lookup((v << SHIFT) | w, m.bk, m.bc)
    back = np.where(
        bi > 0,
        np.log(np.maximum(bi, 1e-9) / np.maximum(m.uni[v], 1)) + model_mod.BACKOFF,
        np.log(np.maximum(m.uni[w], 0.5) / m.total) + 2 * model_mod.BACKOFF,
    )
    return m.tc * np.abs(own - back), u, v, w


def bigram_weights(m):
    v, w = m.bk >> SHIFT, m.bk & MASK
    own = np.log(m.bc / np.maximum(m.uni[v], 1)) + model_mod.BACKOFF
    back = np.log(np.maximum(m.uni[w], 0.5) / m.total) + 2 * model_mod.BACKOFF
    return m.bc * np.abs(own - back), v, w


def select(m, entries, min_plain, seed=None, max_bytes=None):
    """Keeps `entries` n-grams in all, among those whose words the table keeps, or with max_bytes as
    many as fit in a table file of that size."""
    words = kept_words(m, min_plain)
    tw, u, v, w = trigram_weights(m)
    bw, bv, bwd = bigram_weights(m)
    if seed is not None:
        rng = np.random.default_rng(seed)
        tw, bw = rng.random(len(tw)), rng.random(len(bw))
    tw = np.where(words[u] & words[v] & words[w], tw, -1.0)
    bw = np.where(words[bv] & words[bwd], bw, -1.0)
    # A context bigram weighs at least as much as its heaviest trigram, so it is kept first.
    has_ctx = ~((u == BOS) & (v == BOS))
    ctx_key = ((u << SHIFT) | v)[has_ctx]
    ctx_pos = np.minimum(np.searchsorted(m.bk, ctx_key), len(m.bk) - 1)
    assert (m.bk[ctx_pos] == ctx_key).all(), "a trigram's context is not a bigram"
    np.maximum.at(bw, ctx_pos, tw[has_ctx])
    weights = np.concatenate([tw, bw])
    order = np.argsort(-weights, kind="stable")
    if max_bytes is not None:
        entries = fitting(m, order >= len(tw), max_bytes, min_plain)
    cut = weights[order[entries - 1]]
    keep_t, keep_b = tw >= cut, bw >= cut
    assert keep_b[ctx_pos[keep_t[has_ctx]]].all(), "a kept trigram lost its context"
    m.tk, m.tc = m.tk[keep_t], m.tc[keep_t]
    m.bk, m.bc = m.bk[keep_b], m.bc[keep_b]


def fitting(m, is_bigram, max_bytes, min_plain):
    """Most n-grams, taken in weight order, whose table fits in max_bytes."""
    n_bi = np.cumsum(is_bigram)
    n_tri = np.arange(1, len(is_bigram) + 1) - n_bi
    n_words = int(kept_words(m, min_plain).sum())
    free = max_bytes - table.fixed_bytes(m, min_plain)
    # Two start arrays, two id arrays and two count arrays, each padded by at most 7 bytes.
    size = 10 * n_bi + 6 * n_tri + 4 * (n_words + 1) + 4 * 2 + 6 * 7
    return int(np.searchsorted(size, free, side="right"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("out")
    size = ap.add_mutually_exclusive_group(required=True)
    size.add_argument("--entries", type=int, help="bigrams plus trigrams to keep")
    size.add_argument("--bytes", type=int, help="largest table file to write")
    ap.add_argument("--min-plain", type=int, default=0)
    ap.add_argument("--random", type=int, default=None, metavar="SEED")
    a = ap.parse_args()
    m = Model(a.model)
    select(m, a.entries, a.min_plain, a.random, a.bytes)
    print(f"kept {len(m.bk):,} bigrams and {len(m.tk):,} trigrams", flush=True)
    table.write(m, a.out, a.min_plain)


if __name__ == "__main__":
    main()
