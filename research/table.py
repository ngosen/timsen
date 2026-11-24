"""Writes a pruned model as the fixed binary table the library maps from disk, and reads it back.

usage: python -m research.table MODEL.npz OUT.timsen --min-tri N --min-bi N [--min-plain N]

Layout, little-endian, each section padded to a multiple of 8 bytes:
  header    8s magic, u32 version, u32 n_long, u64 n_words n_bigrams n_trigrams n_plain n_cand, f64 total
  words     u32 offsets[n_words + 1], UTF-8 bytes; ids 0, 1, 2 are <s>, </s>, <unk>
  uni       u32 counts[n_words]; the count of <s> is not stored, it equals the count of </s>
  levels    f64 count[256], f64 left[256], f64 left_bos; what a count code and a leftover code stand for,
            and the leftover of the (<s>, <s>) context
  left_uni  f64[n_words]; the leftover of each word as a context
  bigrams   u32 start[n_words + 1], u16 next[n_bigrams], u8 code[n_bigrams], u8 left[n_bigrams]; the
            bigrams starting with word v are next[start[v]:start[v + 1]], ascending
  trigrams  u32 base[(n_bigrams + 1) // 32 + 1], u8 length[n_bigrams + 1], u32 long_group[n_long],
            u32 long_length[n_long], u16 next[n_trigrams], u8 code[n_trigrams]; group j holds the
            trigrams whose first two words are bigram j, ascending, and the last group those after
            (<s>, <s>). Group j starts at base[j // 32] plus the lengths of the groups from
            32 * (j // 32) up to j. A length of 255 stands for the long_length of that group, listed
            in long_group, ascending
  plain     u32 offsets[n_plain + 1], UTF-8 bytes; unmarked forms, ascending by bytes
  cand      u32 start[n_plain + 1], u32 ids[n_cand]; spellings of plain form i are ids[start[i]:start[i + 1]]
Ids fit in 16 bits, so a table holds at most 65,536 words. Every trigram's first two words are a
bigram of the table. A plain form missing from the table restores as itself (<unk>).

A count is stored as the nearest of 256 levels spaced evenly in log, which restore cannot tell from
the exact count. The leftover (Model.index_leftover) is taken from the exact counts when the table
is written, so reading a table needs no pass over its n-grams. Every float but the total is rounded
to single precision before it is stored.
"""

import argparse
import mmap
import struct
from collections import defaultdict

import numpy as np

from .model import BOS, EOS, FLOOR, SHIFT, UNK, Model

MAGIC = b"TIMSEN\0\0"
VERSION = 3
LEVELS = 256
LONG = 255  # a trigram group this long or longer has its length in the long list
BLOCK = 32  # trigram groups per stored base
MAX_WORDS = 1 << 16
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


def padded(n):
    return n + -n % 8


def ngram_bytes(n_words, n_bi, n_tri, n_long):
    """Bytes the bigram and trigram sections take in a file."""
    groups = n_bi + 1
    parts = (4 * (n_words + 1), 2 * n_bi, n_bi, n_bi, 4 * (groups // BLOCK + 1), groups, 4 * n_long, 4 * n_long)
    return sum(padded(n) for n in (*parts, 2 * n_tri, n_tri))


def portable(a):
    """a rounded to single precision: exp and log differ in the last bit from one CPU to another, and
    the same model must give the same file everywhere."""
    return np.asarray(a, dtype=np.float64).astype(np.float32).astype(np.float64)


def count_levels(top):
    """The counts the 256 codes stand for: evenly spaced in log from 1 to the largest count."""
    step = np.log(max(top, 2.0)) / (LEVELS - 1)
    return portable(np.exp(np.arange(LEVELS) * step))


def count_codes(counts, levels):
    step = np.log(levels[-1]) / (LEVELS - 1)
    return np.clip(np.rint(np.log(np.maximum(counts, 1)) / step), 0, LEVELS - 1).astype(np.uint8)


LEFT_LEVELS = portable(np.linspace(np.log(FLOOR), 0.0, LEVELS))


def left_codes(left):
    step = -np.log(FLOOR) / (LEVELS - 1)
    return np.clip(np.rint((left - np.log(FLOOR)) / step), 0, LEVELS - 1).astype(np.uint8)


def u16(a):
    a = np.asarray(a)
    assert a.size == 0 or a.max() < MAX_WORDS, "word id does not fit in 16 bits"
    return a.astype("<u2").tobytes()


def trigram_groups(tri_start):
    """base, length and the long list for the trigram groups that start at tri_start."""
    lengths = np.diff(tri_start)
    long_group = np.flatnonzero(lengths >= LONG)
    short = np.where(lengths >= LONG, LONG, lengths).astype(np.uint8)
    return tri_start[::BLOCK], short, long_group, lengths[long_group]


def ngram_sections(bk, bc, tk, tc, n_words, levels, left_bi):
    """Groups bigrams by first word and trigrams by first two words, as the file stores them."""
    bi_start = np.searchsorted(bk >> np.uint64(SHIFT), np.arange(n_words + 1, dtype=np.uint64))
    ctx = tk >> np.uint64(SHIFT)
    at_start = ctx == 0  # (<s>, <s>): BOS is 0, and its range goes last
    order = np.concatenate([np.flatnonzero(~at_start), np.flatnonzero(at_start)])
    pos = np.searchsorted(bk, ctx[~at_start])
    found = pos < len(bk)
    found[found] = bk[pos[found]] == ctx[~at_start][found]
    assert found.all(), "a trigram's first two words are not a bigram of the table"
    ctx_index = np.concatenate([pos, np.full(int(at_start.sum()), len(bk))])
    tri_start = np.searchsorted(ctx_index, np.arange(len(bk) + 2))
    mask = np.uint64(MASK)
    base, length, long_group, long_length = trigram_groups(tri_start)
    bigrams = [u32(bi_start), u16(bk & mask), count_codes(bc, levels).tobytes(), left_codes(left_bi).tobytes()]
    trigrams = [u32(base), length.tobytes(), u32(long_group), u32(long_length)]
    return [*bigrams, *trigrams, u16(tk[order] & mask), count_codes(tc[order], levels).tobytes()], len(long_group)


def kept_words(m, min_plain):
    opts = options_table(m, min_plain)
    keep = sorted({BOS, EOS, UNK, *(i for ids in opts.values() for i in ids)})
    assert len(keep) <= MAX_WORDS, f"{len(keep)} words do not fit in a table"
    return opts, keep


def other_sections(m, opts, keep, new_id):
    uni = m.uni[keep].copy()
    uni[BOS] = 0
    start = np.zeros(len(opts) + 1, dtype=np.uint32)
    start[1:] = np.cumsum([len(ids) for ids in opts.values()])
    cand = new_id[[i for ids in opts.values() for i in ids]]
    w_off, w_blob = strings(m.words[i] for i in keep)
    p_off, p_blob = strings(opts)
    return [u32(w_off), w_blob, u32(uni)], [u32(p_off), p_blob, u32(start), u32(cand)], len(cand)


def fixed_bytes(m, min_plain=0):
    """Bytes a table of m takes apart from its bigrams and trigrams."""
    opts, keep = kept_words(m, min_plain)
    new_id = np.full(len(m.words), -1, dtype=np.int64)
    new_id[keep] = np.arange(len(keep))
    head, tail, _ = other_sections(m, opts, keep, new_id)
    levels = 8 * (2 * LEVELS + 1) + padded(8 * len(keep))
    return padded(HEADER.size) + levels + sum(padded(len(s)) for s in head + tail)


def remapped(m, keep, bk, bc, tk, tc):
    """The model a table of these n-grams holds, for taking the leftover from its exact counts."""
    t = Model.__new__(Model)
    t.words = [m.words[i] for i in keep]
    t.uni = m.uni[keep].copy()
    t.nseg = m.nseg
    t.bk, t.bc, t.tk, t.tc = bk.astype(np.int64), bc, tk.astype(np.int64), tc
    t.index_leftover()
    return t


def write(m, path, min_plain=0):
    opts, keep = kept_words(m, min_plain)
    new_id = np.full(len(m.words), -1, dtype=np.int64)
    new_id[keep] = np.arange(len(keep))
    bk, bc = remap_keys(m.bk.astype(np.uint64), m.bc, new_id, 2)
    tk, tc = remap_keys(m.tk.astype(np.uint64), m.tc, new_id, 3)
    head, tail, n_cand = other_sections(m, opts, keep, new_id)
    t = remapped(m, keep, bk, bc, tk, tc)
    levels = count_levels(max(bc.max(initial=1), tc.max(initial=1)))
    f64 = np.concatenate([levels, LEFT_LEVELS, portable([t.left_bos])]).astype("<f8").tobytes()
    grams, n_long = ngram_sections(bk, bc, tk, tc, len(keep), levels, t.left_bi)
    header = HEADER.pack(MAGIC, VERSION, n_long, len(keep), len(bk), len(tk), len(opts), n_cand, m.total)
    sections = [header, *head, f64, portable(t.left_uni).astype("<f8").tobytes(), *grams, *tail]
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
    magic, version, n_long, n_words, n_bi, n_tri, n_plain, n_cand, total = HEADER.unpack_from(buf)
    assert magic == MAGIC and version == VERSION, f"{path}: not a version {VERSION} table"
    r = Reader(buf)
    r.pos = -(-HEADER.size // 8) * 8
    m = Model.__new__(Model)
    m.words = r.strings(n_words)
    m.id = {w: i for i, w in enumerate(m.words)}
    m.uni = r.array("<u4", n_words).astype(np.float64)
    m.nseg = m.uni[BOS] = m.uni[EOS]
    m.total = total
    f64 = r.array("<f8", 2 * LEVELS + 1)
    levels, left_levels, m.left_bos = f64[:LEVELS], f64[LEVELS : 2 * LEVELS], f64[-1]
    m.left_uni = r.array("<f8", n_words)
    bi_start, bi_next = r.array("<u4", n_words + 1), r.array("<u2", n_bi).astype(np.int64)
    m.bc = levels[r.array("u1", n_bi)]
    m.left_bi = left_levels[r.array("u1", n_bi)]
    m.bk = (np.repeat(np.arange(n_words, dtype=np.int64), np.diff(bi_start)) << SHIFT) | bi_next
    m.left_keys = m.bk
    base, lengths = r.array("<u4", (n_bi + 1) // BLOCK + 1), r.array("u1", n_bi + 1).astype(np.int64)
    long_group = r.array("<u4", n_long)
    lengths[long_group] = r.array("<u4", n_long)
    tri_start = np.concatenate([[0], np.cumsum(lengths)])
    assert (tri_start[::BLOCK] == base).all() and tri_start[-1] == n_tri, f"{path}: trigram groups do not add up"
    tri_next = r.array("<u2", n_tri).astype(np.int64)
    tc = levels[r.array("u1", n_tri)]
    tk = (np.repeat(np.append(m.bk, 0), np.diff(tri_start)) << SHIFT) | tri_next
    # The (<s>, <s>) range is stored last but sorts first.
    first = int(tri_start[n_bi])
    m.tk, m.tc = np.concatenate([tk[first:], tk[:first]]), np.concatenate([tc[first:], tc[:first]])
    plain = r.strings(n_plain)
    start, ids = r.array("<u4", n_plain + 1), r.array("<u4", n_cand)
    m.cand = defaultdict(list, {p: list(ids[a:b]) for p, a, b in zip(plain, start[:-1], start[1:])})
    m.qk = m.qc = None
    m.entries = n_words + n_bi + n_tri
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
