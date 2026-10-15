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
}

struct Cursor<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl Cursor<'_> {
    /// Claims `len` bytes and returns where they start; sections are padded to 8 bytes.
    fn take(&mut self, len: usize) -> Result<usize, Error> {
        let start = self.pos;
        let end = start.checked_add(len).ok_or(Error::Format("section too large"))?;
        if end > self.bytes.len() {
            return Err(Error::Format("file is truncated"));
        }
        self.pos = end.next_multiple_of(8).min(self.bytes.len());
        Ok(start)
    }

    fn strings(&mut self, n: usize) -> Result<Strings, Error> {
        let offsets = self.take(4 * (n + 1))?;
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
            std::str::from_utf8(s.bytes(self.bytes, i)).map_err(|_| Error::Format("string is not UTF-8"))?;
        }
        Ok(s)
    }

    fn grams(&mut self, n: usize) -> Result<Grams, Error> {
        Ok(Grams { keys: self.take(8 * n)?, counts: self.take(4 * n)?, n })
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
        let [n_words, n_bi, n_tri, n_plain, n_cand] = [0, 1, 2, 3, 4].map(|i| header_u64(&bytes, i));
        let (n_words, n_bi, n_tri, n_plain, n_cand) = (n_words?, n_bi?, n_tri?, n_plain?, n_cand?);
        if n_words < 3 || n_words > 1 << SHIFT {
            return Err(Error::Format("bad vocabulary size"));
        }
        let total = f64::from_le_bytes(bytes[56..64].try_into().unwrap());
        let mut c = Cursor { bytes: &bytes, pos: HEADER_LEN };
        let words = c.strings(n_words)?;
        let uni = c.take(4 * n_words)?;
        let bigrams = c.grams(n_bi)?;
        let trigrams = c.grams(n_tri)?;
        let plain = c.strings(n_plain)?;
        let cand_start = c.take(4 * (n_plain + 1))?;
        let cand_ids = c.take(4 * n_cand)?;
        for i in 0..=n_plain {
            if u32_at(&bytes, cand_start, i) as usize > n_cand {
                return Err(Error::Format("candidate range out of bounds"));
            }
        }
        for i in 0..n_cand {
            if u32_at(&bytes, cand_ids, i) as usize >= n_words {
                return Err(Error::Format("candidate id out of bounds"));
            }
        }
        Ok(Table { bytes, total, words, uni, bigrams, trigrams, plain, cand_start, cand_ids })
    }

    pub fn word(&self, id: u32) -> &str {
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
        self.lookup(&self.trigrams, (u64::from(u) << (2 * SHIFT)) | (u64::from(v) << SHIFT) | u64::from(w))
    }

    fn lookup(&self, g: &Grams, key: u64) -> f64 {
        let (mut lo, mut hi) = (0, g.n);
        while lo < hi {
            let mid = lo + (hi - lo) / 2;
            match u64_at(&self.bytes, g.keys, mid).cmp(&key) {
                std::cmp::Ordering::Less => lo = mid + 1,
                std::cmp::Ordering::Greater => hi = mid,
                std::cmp::Ordering::Equal => return f64::from(u32_at(&self.bytes, g.counts, mid)),
            }
        }
        0.0
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
