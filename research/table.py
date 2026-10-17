"""Writes a pruned model as the fixed binary table the library maps from disk, and reads it back.

usage: python -m research.table MODEL.npz OUT.timsen --min-tri N --min-bi N [--min-plain N]

Layout, little-endian, each section padded to a multiple of 8 bytes:
  header    8s magic, u32 version, u32 0, u64 n_words n_bigrams n_trigrams n_plain n_cand, f64 total
  words     u32 offsets[n_words + 1], UTF-8 bytes; ids 0, 1, 2 are <s>, </s>, <unk>
  uni       u32 counts[n_words]; the count of <s> is not stored, it equals the count of </s>
  bigrams   u64 keys[n_bigrams] (ascending), u32 counts[n_bigrams]
  trigrams  u64 keys[n_trigrams] (ascending), u32 counts[n_trigrams]
  plain     u32 offsets[n_plain + 1], UTF-8 bytes; unmarked forms, ascending by bytes
  cand      u32 start[n_plain + 1], u32 ids[n_cand]; spellings of plain form i are ids[start[i]:start[i + 1]]
An n-gram key packs its word ids 21 bits each, oldest word highest. A plain form missing from the table
restores as itself (<unk>).
"""

import argparse
import mmap
import struct
from collections import defaultdict

import numpy as np

from .model import BOS, EOS, SHIFT, UNK, Model

MAGIC = b"TIMSEN\0\0"
VERSION = 1
HEADER = struct.Struct("<8sII5Qd")
MASK = (1 << SHIFT) - 1


def options_table(m, min_plain=0):
    """Every plain form restore can look up, with the ids Model.options returns for it. A form whose
    only spelling is itself restores as typed even when missing, so below min_plain it is left out."""
    table = {p: list(ids) for p, ids in m.cand.items()}
    for i, w in enumerate(m.words[3:], 3):
        if w not in table and w.isascii():
            table[w] = [i]
    rare = [p for p, ids in table.items() if ids == [m.id.get(p)] and m.uni[ids[0]] < min_plain]
    for p in rare:
        del table[p]
    return dict(sorted(table.items(), key=lambda kv: kv[0].encode()))


def remap_keys(keys, counts, new_id, n):
    """Drops n-grams that use a dropped word and renumbers the rest. New ids keep the old order, so the
    keys stay sorted."""
    ids = [(keys >> np.uint64(SHIFT * (n - 1 - k))) & np.uint64(MASK) for k in range(n)]
    keep = np.all([new_id[i] >= 0 for i in ids], axis=0)
    out = np.zeros(int(keep.sum()), dtype=np.uint64)
    for k, i in enumerate(ids):
        out |= new_id[i[keep]].astype(np.uint64) << np.uint64(SHIFT * (n - 1 - k))
    assert (np.diff(out.astype(np.int64)) > 0).all()
    return out, counts[keep]


def strings(items):
    blobs = [s.encode() for s in items]
    offsets = np.zeros(len(blobs) + 1, dtype=np.uint32)
    offsets[1:] = np.cumsum([len(b) for b in blobs])
    return offsets, b"".join(blobs)


def pad(b):
    return b + b"\0" * (-len(b) % 8)


def u32(a):
    a = np.asarray(a)
    assert a.size == 0 or (a.min() >= 0 and a.max() < 2**32), "count does not fit in 32 bits"
    return a.astype("<u4").tobytes()


def write(m, path, min_plain=0):
    opts = options_table(m, min_plain)
    keep = sorted({BOS, EOS, UNK, *(i for ids in opts.values() for i in ids)})
    new_id = np.full(len(m.words), -1, dtype=np.int64)
    new_id[keep] = np.arange(len(keep))
    bk, bc = remap_keys(m.bk.astype(np.uint64), m.bc, new_id, 2)
    tk, tc = remap_keys(m.tk.astype(np.uint64), m.tc, new_id, 3)
    uni = m.uni[keep].copy()
    uni[BOS] = 0
    start = np.zeros(len(opts) + 1, dtype=np.uint32)
    start[1:] = np.cumsum([len(ids) for ids in opts.values()])
    cand = new_id[[i for ids in opts.values() for i in ids]]
    w_off, w_blob = strings(m.words[i] for i in keep)
    p_off, p_blob = strings(opts)
    header = HEADER.pack(MAGIC, VERSION, 0, len(keep), len(bk), len(tk), len(opts), len(cand), m.total)
    sections = [header, u32(w_off), w_blob, u32(uni), bk.astype("<u8").tobytes(), u32(bc)]
    sections += [tk.astype("<u8").tobytes(), u32(tc), u32(p_off), p_blob, u32(start), u32(cand)]
    with open(path, "wb") as f:
        for s in sections:
            f.write(pad(s))


class Reader:
    def __init__(self, buf):
        self.buf, self.pos = buf, 0

    def array(self, dtype, n):
        a = np.frombuffer(self.buf, dtype=dtype, count=n, offset=self.pos)
        self.pos += -(-a.nbytes // 8) * 8
        return a

    def strings(self, n):
        offsets = self.array("<u4", n + 1)
        blob = self.array("u1", int(offsets[-1])).tobytes()
        return [blob[a:b].decode() for a, b in zip(offsets[:-1], offsets[1:])]


def read(path):
    """A Model backed by the table file, for checking that the file restores exactly like its source."""
    with open(path, "rb") as f:
        buf = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    magic, version, _, n_words, n_bi, n_tri, n_plain, n_cand, total = HEADER.unpack_from(buf)
    assert magic == MAGIC and version == VERSION, f"{path}: not a version {VERSION} table"
    r = Reader(buf)
    r.pos = -(-HEADER.size // 8) * 8
    m = Model.__new__(Model)
    m.words = r.strings(n_words)
    m.id = {w: i for i, w in enumerate(m.words)}
    m.uni = r.array("<u4", n_words).astype(np.float64)
    m.nseg = m.uni[BOS] = m.uni[EOS]
    m.total = total
    m.bk, m.bc = r.array("<u8", n_bi).astype(np.int64), r.array("<u4", n_bi).astype(np.float64)
    m.tk, m.tc = r.array("<u8", n_tri).astype(np.int64), r.array("<u4", n_tri).astype(np.float64)
    plain = r.strings(n_plain)
    start, ids = r.array("<u4", n_plain + 1), r.array("<u4", n_cand)
    m.cand = defaultdict(list, {p: list(ids[a:b]) for p, a, b in zip(plain, start[:-1], start[1:])})
    m.qk = m.qc = None
    m.entries = n_words + n_bi + n_tri
    m.index_leftover()
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("out")
    ap.add_argument("--min-tri", type=int, default=1)
    ap.add_argument("--min-bi", type=int, default=1)
    ap.add_argument("--min-plain", type=int, default=0, help="leave out rarer words that restore as typed")
    a = ap.parse_args()
    write(Model(a.model, a.min_tri, a.min_bi), a.out, a.min_plain)


if __name__ == "__main__":
    main()
