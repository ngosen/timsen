"""Syllable 3- or 4-gram model with stupid backoff, and Viterbi restoration of a run of unmarked syllables."""

from collections import defaultdict

import numpy as np

from .text import strip_marks

BOS, EOS, UNK = 0, 1, 2
SHIFT = 21  # bits per word id in packed n-gram keys
MIN_CANDIDATE = 5  # rarer spellings are mostly typos in the corpus
BACKOFF = np.log(0.4)
MIX = np.uint64(0x9E3779B97F4A7C15)


def quad_key(t, u, v, w):
    """Four 21-bit ids do not fit in 64 bits, so 4-grams are keyed by a hash; collisions are rare enough
    to ignore for counts."""
    tri = np.asarray((t << (2 * SHIFT)) | (u << SHIFT) | v).astype(np.uint64)
    k = (tri * MIX) ^ np.asarray(w).astype(np.uint64)
    k ^= k >> np.uint64(31)
    k *= np.uint64(0xBF58476D1CE4E5B9)
    return k ^ (k >> np.uint64(29))


class Model:
    def __init__(self, path, min_tri=1, min_bi=1):
        z = np.load(path)
        self.words = list(z["words"])
        self.id = {w: i for i, w in enumerate(self.words)}
        self.uni = z["uni"].astype(np.float64)
        self.nseg = self.uni[EOS]
        self.uni[BOS] = self.nseg
        self.total = self.uni[3:].sum() + self.nseg
        keep = z["bc"] >= min_bi
        self.bk, self.bc = z["bk"][keep], z["bc"][keep].astype(np.float64)
        keep = z["tc"] >= min_tri
        self.tk, self.tc = z["tk"][keep], z["tc"][keep].astype(np.float64)
        self.qk = z["qk"] if "qk" in z.files else None
        self.qc = z["qc"].astype(np.float64) if self.qk is not None else None
        self.cand = defaultdict(list)
        for i, w in enumerate(self.words[3:], 3):
            if self.uni[i] >= MIN_CANDIDATE:
                self.cand[strip_marks(w)].append(i)
        self.entries = len(self.words) + len(self.bk) + len(self.tk) + (len(self.qk) if self.qk is not None else 0)

    def snapshot(self):
        return (self.uni.copy(), self.bk, self.bc, self.tk, self.tc, self.nseg, self.total)

    def restore_snapshot(self, s):
        self.uni, self.bk, self.bc, self.tk, self.tc, self.nseg, self.total = s
        self.uni = self.uni.copy()

    @staticmethod
    def lookup(keys, table, counts):
        if len(table) == 0:
            return np.zeros(np.shape(keys))
        pos = np.minimum(np.searchsorted(table, keys), len(table) - 1)
        return np.where(table[pos] == keys, counts[pos], 0.0)

    def logp(self, u, v, w):
        """Log score of w after (u, v); the arguments broadcast against each other."""
        u, v, w = np.broadcast_arrays(u, v, w)
        tri = self.lookup((u << (2 * SHIFT)) | (v << SHIFT) | w, self.tk, self.tc)
        ctx = self.lookup((u << SHIFT) | v, self.bk, self.bc)
        ctx = np.where((u == BOS) & (v == BOS), self.nseg, ctx)
        bi = self.lookup((v << SHIFT) | w, self.bk, self.bc)
        p_uni = np.log(np.maximum(self.uni[w], 0.5) / self.total) + 2 * BACKOFF
        p_bi = np.log(np.maximum(bi, 1e-9) / np.maximum(self.uni[v], 1)) + BACKOFF
        p_tri = np.log(np.maximum(tri, 1e-9) / np.maximum(ctx, 1))
        return np.where(tri > 0, p_tri, np.where(bi > 0, p_bi, p_uni))

    def logp4(self, t, u, v, w):
        """Log score of w after (t, u, v); falls back to logp when the 4-gram was not seen."""
        t, u, v, w = np.broadcast_arrays(t, u, v, w)
        quad = self.lookup(quad_key(t, u, v, w), self.qk, self.qc)
        ctx = self.lookup((t << (2 * SHIFT)) | (u << SHIFT) | v, self.tk, self.tc)
        p3 = self.logp(u, v, w)
        # Runs start with two BOS, so (BOS, BOS, BOS) is not a context: the trigram is the top order there.
        p3 = np.where((t == BOS) & (u == BOS) & (v == BOS), p3, p3 + BACKOFF)
        return np.where(quad > 0, np.log(np.maximum(quad, 1e-9) / np.maximum(ctx, 1)), p3)

    def options(self, plain):
        c = self.cand.get(plain)
        return np.array(c if c else [self.id.get(plain, UNK)], dtype=np.int64)

    def word(self, i, plain):
        return plain if i == UNK else self.words[i]

    def restore(self, plain_words):
        """Best marked spelling for each unmarked syllable, using the whole run (left and right context)."""
        if self.qk is not None:
            return self.restore4(plain_words)
        opts = [self.options(p) for p in plain_words]
        pp_opts = np.array([BOS], dtype=np.int64)
        prev_opts = np.array([BOS], dtype=np.int64)
        score = np.zeros((1, 1))  # score[a, b]: best path ending with candidates a (previous), b (current)
        back = []
        for o in opts:
            s = score[:, :, None] + self.logp(pp_opts[:, None, None], prev_opts[None, :, None], o[None, None, :])
            back.append(s.argmax(axis=0))
            score = s.max(axis=0)
            pp_opts, prev_opts = prev_opts, o
        final = score + self.logp(pp_opts[:, None], prev_opts[None, :], np.int64(EOS))
        a, b = np.unravel_index(final.argmax(), final.shape)
        picks = [b, a]
        for bp in reversed(back[2:]):
            a, b = bp[a, b], a
            picks.append(a)
        picks = picks[: len(opts)][::-1]
        return [self.word(opts[i][k], plain_words[i]) for i, k in enumerate(picks)]

    def restore4(self, plain_words):
        """restore with the last three candidates as the Viterbi state."""
        opts = [self.options(p) for p in plain_words]
        bos = np.array([BOS], dtype=np.int64)
        hist = [bos, bos, bos]
        score = np.zeros((1, 1, 1))  # score[a, b, c]: best path ending with candidates a, b, c
        back = []
        for o in opts:
            a, b, c = hist
            s = score[..., None] + self.logp4(
                a[:, None, None, None], b[None, :, None, None], c[None, None, :, None], o[None, None, None, :]
            )
            back.append(s.argmax(axis=0))
            score = s.max(axis=0)
            hist = [b, c, o]
        a, b, c = hist
        final = score + self.logp4(a[:, None, None], b[None, :, None], c[None, None, :], np.int64(EOS))
        a, b, c = np.unravel_index(final.argmax(), final.shape)
        picks = [c, b, a]
        for bp in reversed(back[3:]):
            a, b, c = bp[a, b, c], a, b
            picks.append(a)
        picks = picks[: len(opts)][::-1]
        return [self.word(opts[i][k], plain_words[i]) for i, k in enumerate(picks)]

    def restore_unigram(self, plain_words):
        out = []
        for p in plain_words:
            o = self.options(p)
            out.append(self.word(o[self.uni[o].argmax()], p))
        return out
