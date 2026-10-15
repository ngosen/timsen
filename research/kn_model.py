"""Back-off n-gram model read from a KenLM ARPA file, and beam-search restoration.

usage: python -m research.kn_model convert MODEL.arpa OUT.npz
       python -m research.kn_model eval OUT.npz CANDIDATES.npz TESTFILE...

CANDIDATES.npz is a model from research.train on the same corpora: its counts decide which spellings
are candidates (MIN_CANDIDATE), so both models choose among the same words.
"""

import math
import sys
from collections import defaultdict

import numpy as np

from .evaluate import evaluate
from .model import MIN_CANDIDATE
from .text import strip_marks

BITS = 16  # four 16-bit ids pack into one 64-bit key; kn_export caps the vocabulary to fit
LN10 = math.log(10)
BEAM = 64


def pack(ids):
    key = np.zeros(ids.shape[0], dtype=np.uint64)
    for col in range(ids.shape[1]):
        key = (key << np.uint64(BITS)) | ids[:, col].astype(np.uint64)
    return key


def convert(arpa, out):
    """Reads an ARPA file into sorted packed keys per order; arrays are sized from the header."""
    sizes, words, index, arrays = {}, [], {}, {}
    order = row = 0
    with open(arpa, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("ngram "):
                n, count = line[6:].split("=")
                sizes[int(n)] = int(count)
            elif line.startswith("\\") and line.endswith("-grams:"):
                order, row = int(line[1:].split("-")[0]), 0
                keys = np.zeros(sizes[order], dtype=np.uint64)
                prob = np.zeros(sizes[order], dtype=np.float32)
                bo = np.zeros(sizes[order], dtype=np.float32)
                arrays[order] = (keys, prob, bo)
            elif order and line and not line.startswith("\\"):
                parts = line.split("\t")
                gram = parts[1].split(" ")
                if order == 1:
                    index[gram[0]] = len(words)
                    words.append(gram[0])
                key = 0
                for w in gram:
                    key = (key << BITS) | index[w]
                keys[row] = key
                prob[row] = float(parts[0]) * LN10
                bo[row] = float(parts[2]) * LN10 if len(parts) > 2 else 0.0
                row += 1
    saved = {"words": np.array(words)}
    for n, (keys, prob, bo) in arrays.items():
        idx = np.argsort(keys)
        saved[f"k{n}"], saved[f"p{n}"], saved[f"b{n}"] = keys[idx], prob[idx], bo[idx]
    np.savez(out, **saved)


class KNModel:
    def __init__(self, path, candidates_path):
        z = np.load(path)
        self.words = list(z["words"])
        self.id = {w: i for i, w in enumerate(self.words)}
        self.order = max(int(k[1:]) for k in z.files if k.startswith("k"))
        self.tables = {n: (z[f"k{n}"], z[f"p{n}"], z[f"b{n}"]) for n in range(1, self.order + 1)}
        self.unk, self.bos, self.eos = self.id["<unk>"], self.id["<s>"], self.id["</s>"]
        c = np.load(candidates_path)
        self.cand = defaultdict(list)
        for w, n in zip(c["words"][3:], c["uni"][3:]):
            if n >= MIN_CANDIDATE and w in self.id:
                self.cand[strip_marks(w)].append(self.id[w])

    def find(self, n, ids):
        keys, prob, bo = self.tables[n]
        k = pack(ids)
        pos = np.minimum(np.searchsorted(keys, k), len(keys) - 1)
        hit = keys[pos] == k
        return hit, np.where(hit, prob[pos], 0.0), np.where(hit, bo[pos], 0.0)

    def logp(self, hist, w):
        """hist: (M, order-1) previous ids, oldest first; w: (M,) ids. Standard back-off score."""
        m = len(w)
        score = np.zeros(m)
        done = np.zeros(m, dtype=bool)
        for n in range(self.order, 0, -1):
            ctx = hist[:, hist.shape[1] - (n - 1) :] if n > 1 else hist[:, :0]
            gram = np.concatenate([ctx, w[:, None]], axis=1)
            hit, p, _ = self.find(n, gram)
            take = hit & ~done
            score[take] += p[take]
            done |= hit
            if n > 1:
                chit, _, b = self.find(n - 1, ctx)
                add = ~done & chit
                score[add] += b[add]
        return score

    def options(self, plain):
        c = self.cand.get(plain)
        return c if c else [self.id.get(plain, self.unk)]

    def restore(self, plain_words):
        width = self.order - 1
        beams = [((self.bos,) * width, 0.0, [])]
        for plain in plain_words:
            opts = self.options(plain)
            hist = np.array([b[0] for b in beams for _ in opts], dtype=np.int64)
            w = np.array([o for _ in beams for o in opts], dtype=np.int64)
            s = self.logp(hist, w)
            best = {}
            for i, (b, o) in enumerate((b, o) for b in beams for o in opts):
                state = (*b[0][1:], o)
                total = b[1] + s[i]
                if state not in best or total > best[state][1]:
                    best[state] = (state, total, b[2] + [o])
            beams = sorted(best.values(), key=lambda x: -x[1])[:BEAM]
        hist = np.array([b[0] for b in beams], dtype=np.int64)
        final = self.logp(hist, np.full(len(beams), self.eos, dtype=np.int64))
        top = beams[int(np.argmax([b[1] for b in beams] + final))]
        return [plain if i == self.unk else self.words[i] for plain, i in zip(plain_words, top[2])]


def main():
    if sys.argv[1] == "convert":
        convert(sys.argv[2], sys.argv[3])
        return
    m = KNModel(sys.argv[2], sys.argv[3])
    print(f"{sys.argv[2]}: order {m.order}, vocab {len(m.words):,}", flush=True)
    for test in sys.argv[4:]:
        r = evaluate(m, test, m.restore)
        print(
            f"  {test.rsplit('/', 1)[-1]:12} words {r['words']:6} word {r['word']:.2%} sent {r['sent']:.2%} "
            f"marked-right {r['marked_right']:.2%} plain-changed {r['plain_changed']:.2%}",
            flush=True,
        )


if __name__ == "__main__":
    main()
