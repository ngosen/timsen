//! Reader for the `.timsen` table written by `research.table`; the layout is documented there.
//!
//! Every section is read in place: opening a table checks the header and the string sections, and
//! lookups decode little-endian numbers straight from the mapped bytes.

use std::fmt;
use std::fs::File;
use std::ops::{Deref, Range};
use std::path::Path;

pub const BOS: u32 = 0;
pub const EOS: u32 = 1;
pub const UNK: u32 = 2;
/// Bits per word id in packed n-gram keys.
pub const SHIFT: u32 = 21;

const MAGIC: &[u8; 8] = b"TIMSEN\0\0";
const VERSION: u32 = 1;
const HEADER_LEN: usize = 64;
/// Most spellings one unmarked form may have, far above what real tables use. Typing keeps a score
/// for every pair of neighbouring spellings, so this bounds its memory per syllable.
pub(crate) const MAX_SPELLINGS: usize = 256;

#[derive(Debug)]
pub enum Error {
    Io(std::io::Error),
    Format(&'static str),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Io(e) => write!(f, "cannot read table: {e}"),
            Error::Format(why) => write!(f, "not a valid table: {why}"),
        }
    }
}

impl std::error::Error for Error {}

impl From<std::io::Error> for Error {
    fn from(e: std::io::Error) -> Self {
        Error::Io(e)
    }
}

enum Bytes {
    Mapped(memmap2::Mmap),
    Owned(Vec<u8>),
}

impl Deref for Bytes {
    type Target = [u8];
    fn deref(&self) -> &[u8] {
        match self {
            Bytes::Mapped(m) => m,
            Bytes::Owned(v) => v,
        }
    }
}

/// Byte positions of a string section: `n + 1` u32 offsets, then the UTF-8 blob.
struct Strings {
    offsets: usize,
    blob: usize,
    n: usize,
}

/// Byte positions of an n-gram section: ascending u64 keys, then u32 counts.
struct Grams {
    keys: usize,
    counts: usize,
    n: usize,
}

pub struct Table {
    bytes: Bytes,
    total: f64,
    words: Strings,
    uni: usize,
    bigrams: Grams,
    trigrams: Grams,
    plain: Strings,
    cand_start: usize,
    cand_ids: usize,
    left: Left,
}

/// How much of each context's count the kept longer n-grams leave uncovered, read once at load.
struct Left {
    /// Per bigram, the summed counts of its kept trigram continuations.
    kept: Vec<u32>,
    /// Log unkept share of the (`<s>`, `<s>`) context.
    bos: f64,
    /// Per word, the log unkept share of its count.
    uni: Vec<f64>,
}

/// Smallest unkept share, so a context that kept everything still has a finite cost.
const FLOOR: f64 = 1e-4;

fn log_share(kept: f64, count: f64) -> f64 {
    (1.0 - kept / count).clamp(FLOOR, 1.0).ln()
}

struct Cursor<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl Cursor<'_> {
    /// Claims `len` bytes and returns where they start; sections are padded to 8 bytes.
    fn take(&mut self, len: usize) -> Result<usize, Error> {
        let start = self.pos;
        let end = start
            .checked_add(len)
            .ok_or(Error::Format("section too large"))?;
        if end > self.bytes.len() {
            return Err(Error::Format("file is truncated"));
        }
        self.pos = end.next_multiple_of(8).min(self.bytes.len());
        Ok(start)
    }

    /// Claims `n` items of `size` bytes each.
    fn take_n(&mut self, n: usize, size: usize) -> Result<usize, Error> {
        let len = n
            .checked_mul(size)
            .ok_or(Error::Format("section too large"))?;
        self.take(len)
    }

    fn strings(&mut self, n: usize) -> Result<Strings, Error> {
        let offsets = self.take_n(
            n.checked_add(1).ok_or(Error::Format("section too large"))?,
            4,
        )?;
        let blob_len = u32_at(self.bytes, offsets, n) as usize;
        let blob = self.take(blob_len)?;
        let mut last = 0;
        for i in 0..=n {
            let off = u32_at(self.bytes, offsets, i) as usize;
            if off < last || off > blob_len {
                return Err(Error::Format("string offsets out of order"));
            }
            last = off;
        }
        let s = Strings { offsets, blob, n };
        for i in 0..n {
            std::str::from_utf8(s.bytes(self.bytes, i))
                .map_err(|_| Error::Format("string is not UTF-8"))?;
        }
        Ok(s)
    }

    fn grams(&mut self, n: usize) -> Result<Grams, Error> {
        Ok(Grams {
            keys: self.take_n(n, 8)?,
            counts: self.take_n(n, 4)?,
            n,
        })
    }
}

impl Strings {
    fn bytes<'a>(&self, bytes: &'a [u8], i: usize) -> &'a [u8] {
        let a = u32_at(bytes, self.offsets, i) as usize;
        let b = u32_at(bytes, self.offsets, i + 1) as usize;
        &bytes[self.blob + a..self.blob + b]
    }
}

fn u32_at(bytes: &[u8], pos: usize, i: usize) -> u32 {
    let p = pos + 4 * i;
    u32::from_le_bytes(bytes[p..p + 4].try_into().unwrap())
}

fn u64_at(bytes: &[u8], pos: usize, i: usize) -> u64 {
    let p = pos + 8 * i;
    u64::from_le_bytes(bytes[p..p + 8].try_into().unwrap())
}

/// Every unmarked form has 1 to `MAX_SPELLINGS` distinct spellings, in ranges that tile the ids.
fn check_candidates(
    bytes: &[u8],
    start: usize,
    ids: usize,
    n_plain: usize,
    n_cand: usize,
    n_words: usize,
) -> Result<(), Error> {
    if u32_at(bytes, start, 0) != 0 || u32_at(bytes, start, n_plain) as usize != n_cand {
        return Err(Error::Format("candidate ranges do not cover the ids"));
    }
    let mut seen = Vec::with_capacity(MAX_SPELLINGS);
    for i in 0..n_plain {
        let (a, b) = (
            u32_at(bytes, start, i) as usize,
            u32_at(bytes, start, i + 1) as usize,
        );
        if b <= a || b - a > MAX_SPELLINGS || b > n_cand {
            return Err(Error::Format("bad number of spellings"));
        }
        seen.clear();
        for j in a..b {
            let id = u32_at(bytes, ids, j);
            if id as usize >= n_words {
                return Err(Error::Format("candidate id out of bounds"));
            }
            if seen.contains(&id) {
                return Err(Error::Format("repeated spelling"));
            }
            seen.push(id);
        }
    }
    Ok(())
}

fn header_u64(bytes: &[u8], i: usize) -> Result<usize, Error> {
    usize::try_from(u64_at(bytes, 16, i)).map_err(|_| Error::Format("count too large"))
}

impl Table {
    /// Maps a table file from disk.
    pub fn open(path: impl AsRef<Path>) -> Result<Table, Error> {
        let file = File::open(path)?;
        // SAFETY: the file is opened read-only; a table replaced while mapped is the caller's error,
        // as with any memory-mapped data file.
        let map = unsafe { memmap2::Mmap::map(&file)? };
        Table::parse(Bytes::Mapped(map))
    }

    /// Reads a table already in memory.
    pub fn from_bytes(bytes: Vec<u8>) -> Result<Table, Error> {
        Table::parse(Bytes::Owned(bytes))
    }

    fn parse(bytes: Bytes) -> Result<Table, Error> {
        if bytes.len() < HEADER_LEN || &bytes[..8] != MAGIC {
            return Err(Error::Format("missing magic number"));
        }
        if u32_at(&bytes, 8, 0) != VERSION {
            return Err(Error::Format("unsupported version"));
        }
        let [n_words, n_bi, n_tri, n_plain, n_cand] =
            [0, 1, 2, 3, 4].map(|i| header_u64(&bytes, i));
        let (n_words, n_bi, n_tri, n_plain, n_cand) = (n_words?, n_bi?, n_tri?, n_plain?, n_cand?);
        if !(3..=1 << SHIFT).contains(&n_words) {
            return Err(Error::Format("bad vocabulary size"));
        }
        let total = f64::from_le_bytes(bytes[56..64].try_into().unwrap());
        let mut c = Cursor {
            bytes: &bytes,
            pos: HEADER_LEN,
        };
        let words = c.strings(n_words)?;
        let uni = c.take_n(n_words, 4)?;
        let bigrams = c.grams(n_bi)?;
        let trigrams = c.grams(n_tri)?;
        let plain = c.strings(n_plain)?;
        // n_plain + 1 cannot overflow: the plain strings section above already needed it.
        let cand_start = c.take_n(n_plain + 1, 4)?;
        let cand_ids = c.take_n(n_cand, 4)?;
        check_candidates(&bytes, cand_start, cand_ids, n_plain, n_cand, n_words)?;
        let mut t = Table {
            bytes,
            total,
            words,
            uni,
            bigrams,
            trigrams,
            plain,
            cand_start,
            cand_ids,
            left: Left {
                kept: Vec::new(),
                bos: 0.0,
                uni: Vec::new(),
            },
        };
        t.left = t.index_left();
        Ok(t)
    }

    /// Trigrams are sorted by key, so each context's continuations are adjacent.
    fn index_left(&self) -> Left {
        let (b, g) = (&self.bytes, &self.trigrams);
        let bos_ctx = (u64::from(BOS) << SHIFT) | u64::from(BOS);
        let mut kept = vec![0u32; self.bigrams.n];
        let mut bos_kept = 0u64;
        let mut i = 0;
        while i < g.n {
            let ctx = u64_at(b, g.keys, i) >> SHIFT;
            let mut sum = 0u64;
            while i < g.n && u64_at(b, g.keys, i) >> SHIFT == ctx {
                sum += u64::from(u32_at(b, g.counts, i));
                i += 1;
            }
            if ctx == bos_ctx {
                bos_kept += sum;
            } else if let Some(j) = self.find(&self.bigrams, ctx) {
                kept[j] = kept[j].saturating_add(u32::try_from(sum).unwrap_or(u32::MAX));
            }
        }
        let mut bi_sum = vec![0.0f64; self.len()];
        for j in 0..self.bigrams.n {
            let v = (u64_at(b, self.bigrams.keys, j) >> SHIFT) as usize;
            if let Some(s) = bi_sum.get_mut(v) {
                *s += f64::from(u32_at(b, self.bigrams.counts, j));
            }
        }
        let uni = (0..self.len())
            .map(|id| log_share(bi_sum[id], self.uni(id as u32).max(1.0)))
            .collect();
        Left {
            kept,
            bos: log_share(bos_kept as f64, self.segments().max(1.0)),
            uni,
        }
    }

    /// Log unkept share of context `u v`; a context the table dropped says nothing, so it is 0.
    pub(crate) fn left(&self, u: u32, v: u32) -> f64 {
        if u == BOS && v == BOS {
            return self.left.bos;
        }
        match self.find(&self.bigrams, (u64::from(u) << SHIFT) | u64::from(v)) {
            Some(j) => log_share(
                f64::from(self.left.kept[j]),
                f64::from(u32_at(&self.bytes, self.bigrams.counts, j)),
            ),
            None => 0.0,
        }
    }

    /// Log unkept share of word `v`'s count, as the context of a bigram.
    pub(crate) fn left_uni(&self, v: u32) -> f64 {
        self.left.uni.get(v as usize).copied().unwrap_or(0.0)
    }

    /// Number of words, counting `<s>`, `</s>` and `<unk>`.
    pub(crate) fn len(&self) -> usize {
        self.words.n
    }

    /// Every id of the table is its own context; see `Personal::context`.
    pub(crate) fn context(&self, id: u32) -> u32 {
        id
    }

    pub(crate) fn predicted(&self, id: u32) -> (u32, f64) {
        (id, 0.0)
    }

    /// The spelling of a word id; ids come from the table itself, so they are in range.
    pub(crate) fn word(&self, id: u32) -> &str {
        std::str::from_utf8(self.words.bytes(&self.bytes, id as usize)).unwrap()
    }

    /// Unigram count; `<s>` counts as often as `</s>`, one per run.
    pub(crate) fn uni(&self, id: u32) -> f64 {
        let id = if id == BOS { EOS } else { id };
        f64::from(u32_at(&self.bytes, self.uni, id as usize))
    }

    pub(crate) fn total(&self) -> f64 {
        self.total
    }

    pub(crate) fn segments(&self) -> f64 {
        self.uni(EOS)
    }

    pub(crate) fn bigram(&self, v: u32, w: u32) -> f64 {
        self.lookup(&self.bigrams, (u64::from(v) << SHIFT) | u64::from(w))
    }

    pub(crate) fn trigram(&self, u: u32, v: u32, w: u32) -> f64 {
        self.lookup(
            &self.trigrams,
            (u64::from(u) << (2 * SHIFT)) | (u64::from(v) << SHIFT) | u64::from(w),
        )
    }

    fn lookup(&self, g: &Grams, key: u64) -> f64 {
        self.find(g, key)
            .map_or(0.0, |i| f64::from(u32_at(&self.bytes, g.counts, i)))
    }

    fn find(&self, g: &Grams, key: u64) -> Option<usize> {
        let (mut lo, mut hi) = (0, g.n);
        while lo < hi {
            let mid = lo + (hi - lo) / 2;
            match u64_at(&self.bytes, g.keys, mid).cmp(&key) {
                std::cmp::Ordering::Less => lo = mid + 1,
                std::cmp::Ordering::Greater => hi = mid,
                std::cmp::Ordering::Equal => return Some(mid),
            }
        }
        None
    }

    /// Ids of the spellings of an unmarked syllable, or `None` if the table does not know it.
    pub(crate) fn options(&self, plain: &str) -> Option<impl ExactSizeIterator<Item = u32> + '_> {
        let (mut lo, mut hi) = (0, self.plain.n);
        while lo < hi {
            let mid = lo + (hi - lo) / 2;
            match self.plain.bytes(&self.bytes, mid).cmp(plain.as_bytes()) {
                std::cmp::Ordering::Less => lo = mid + 1,
                std::cmp::Ordering::Greater => hi = mid,
                std::cmp::Ordering::Equal => {
                    let range: Range<usize> = u32_at(&self.bytes, self.cand_start, mid) as usize
                        ..u32_at(&self.bytes, self.cand_start, mid + 1) as usize;
                    return Some(range.map(|i| u32_at(&self.bytes, self.cand_ids, i)));
                }
            }
        }
        None
    }
}
