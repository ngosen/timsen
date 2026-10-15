"""Syllable trigram model with stupid backoff, and Viterbi restoration of a run of unmarked syllables."""

from collections import defaultdict

import numpy as np

from .text import strip_marks

BOS, EOS, UNK = 0, 1, 2
SHIFT = 21  # bits per word id in packed n-gram keys
MIN_CANDIDATE = 5  # rarer spellings are mostly typos in the corpus
BACKOFF = np.log(0.4)


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
        self.cand = defaultdict(list)
        for i, w in enumerate(self.words[3:], 3):
            if self.uni[i] >= MIN_CANDIDATE:
                self.cand[strip_marks(w)].append(i)
        self.entries = len(self.words) + len(self.bk) + len(self.tk)

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

    def options(self, plain):
        c = self.cand.get(plain)
        return np.array(c if c else [self.id.get(plain, UNK)], dtype=np.int64)

    def word(self, i, plain):
        return plain if i == UNK else self.words[i]

    def restore(self, plain_words):
        """Best marked spelling for each unmarked syllable, using the whole run (left and right context)."""
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

    def restore_unigram(self, plain_words):
        out = []
        for p in plain_words:
            o = self.options(p)
            out.append(self.word(o[self.uni[o].argmax()], p))
        return out
