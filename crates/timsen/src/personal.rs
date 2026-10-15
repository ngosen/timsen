//! The personal dictionary: n-gram counts learned from the user's own text, added on top of a table.

use std::collections::HashMap;
use std::io::{BufRead, Write};

use crate::table::{BOS, EOS, SHIFT, UNK};
use crate::{Error, Table, tone};

/// How much one learned n-gram weighs against one seen in the corpora.
pub const WEIGHT: f64 = 100.0;

const HEADER: &str = "timsen-personal 1";
const MAX_ID: u32 = (1 << SHIFT) - 1;

/// Counts learned from text known to be right, for one table. Words the table lacks get ids after
/// the table's own, so they can be guessed too; the saved file names words by their spelling, so it
/// survives a new table.
pub struct Personal<'t> {
    table: &'t Table,
    /// Word `table.len() + i` is `new_words[i]`.
    new_words: Vec<String>,
    new_ids: HashMap<String, u32>,
    /// Learned words an unmarked form does not already offer in the table.
    extra: HashMap<String, Vec<u32>>,
    uni: HashMap<u32, u64>,
    bi: HashMap<u64, u64>,
    tri: HashMap<u64, u64>,
    /// The same n-grams with each learned word the table lacks read as `<unk>` where it is a context,
    /// as the table counts such words. Kept apart so a saved file names only real words.
    unk_uni: u64,
    unk_bi: HashMap<u64, u64>,
    unk_tri: HashMap<u64, u64>,
    /// Learned words the table knows, and run ends: the table's total leaves `<unk>` out.
    tokens: u64,
}

fn key2(v: u32, w: u32) -> u64 {
    (u64::from(v) << SHIFT) | u64::from(w)
}

fn key3(u: u32, v: u32, w: u32) -> u64 {
    (u64::from(u) << (2 * SHIFT)) | key2(v, w)
}

fn get(map: &HashMap<u64, u64>, k: u64) -> u64 {
    map.get(&k).copied().unwrap_or(0)
}

impl<'t> Personal<'t> {
    pub fn new(table: &'t Table) -> Personal<'t> {
        Personal {
            table,
            new_words: Vec::new(),
            new_ids: HashMap::new(),
            extra: HashMap::new(),
            uni: HashMap::new(),
            bi: HashMap::new(),
            tri: HashMap::new(),
            unk_uni: 0,
            unk_bi: HashMap::new(),
            unk_tri: HashMap::new(),
            tokens: 0,
        }
    }

    pub fn table(&self) -> &'t Table {
        self.table
    }

    pub fn is_empty(&self) -> bool {
        self.tokens == 0
    }

    /// Forgets everything learned.
    pub fn clear(&mut self) {
        *self = Personal::new(self.table);
    }

    /// Learns a run of words known to be right: typed with marks, or a guess the user corrected.
    /// `None` stands for a word that is not known to be right; no n-gram is learned across it.
    pub fn learn(&mut self, run: &[Option<&str>]) {
        let ids: Vec<Option<u32>> = run.iter().map(|w| w.and_then(|w| self.intern(w))).collect();
        if ids.iter().all(Option::is_none) {
            return;
        }
        let seq: Vec<Option<u32>> = [Some(BOS), Some(BOS)]
            .into_iter()
            .chain(ids)
            .chain([Some(EOS)])
            .collect();
        for &id in seq[2..].iter().flatten() {
            self.add(&[id], 1);
        }
        for i in 2..seq.len() {
            if let (Some(v), Some(w)) = (seq[i - 1], seq[i]) {
                self.add(&[v, w], 1);
                if let Some(u) = seq[i - 2] {
                    self.add(&[u, v, w], 1);
                }
            }
        }
    }

    /// Counts an n-gram `c` times, and again with words the table lacks read as `<unk>`: in context
    /// position always, and as the last word for the n-grams that serve as a longer one's context.
    fn add(&mut self, ids: &[u32], c: u64) {
        match *ids {
            [w] => {
                *self.uni.entry(w).or_default() += c;
                if self.own(w) {
                    self.tokens += c;
                } else {
                    self.unk_uni += c;
                }
            }
            [v, w] => {
                *self.bi.entry(key2(v, w)).or_default() += c;
                let mut keys = Vec::new();
                if !self.own(v) {
                    keys.push(key2(UNK, w));
                }
                if !self.own(w) {
                    keys.push(key2(self.context(v), UNK));
                }
                for k in keys {
                    *self.unk_bi.entry(k).or_default() += c;
                }
            }
            [u, v, w] => {
                *self.tri.entry(key3(u, v, w)).or_default() += c;
                let mut keys = Vec::new();
                if !self.own(u) || !self.own(v) {
                    keys.push(key3(self.context(u), self.context(v), w));
                }
                if !self.own(w) {
                    keys.push(key3(self.context(u), self.context(v), UNK));
                }
                for k in keys {
                    *self.unk_tri.entry(k).or_default() += c;
                }
            }
            _ => unreachable!("n-grams are one to three words"),
        }
    }

    /// The id a word stands for as a context: words the table lacks are `<unk>` there, so they share
    /// what the table and the other learned words say about unknown words.
    pub(crate) fn context(&self, id: u32) -> u32 {
        if self.own(id) { id } else { UNK }
    }

    /// The id of a word as typed, adding it if the table lacks it; `None` once ids run out.
    fn intern(&mut self, word: &str) -> Option<u32> {
        let word = tone::to_new(&word.to_lowercase());
        let plain = tone::strip(&word);
        let offered: Vec<u32> = self.table.options(&plain).into_iter().flatten().collect();
        if let Some(&id) = offered.iter().find(|&&id| self.table.word(id) == word) {
            return Some(id);
        }
        if let Some(&id) = self.new_ids.get(&word) {
            return Some(id);
        }
        let id = u32::try_from(self.table.len() + self.new_words.len()).ok()?;
        if id > MAX_ID {
            return None;
        }
        self.new_ids.insert(word.clone(), id);
        self.new_words.push(word);
        self.extra.entry(plain).or_default().push(id);
        Some(id)
    }

    /// Spellings of an unmarked syllable: the table's, then learned words it lacks.
    pub(crate) fn options(&self, plain: &str) -> Option<Vec<u32>> {
        let mut ids: Vec<u32> = self.table.options(plain).into_iter().flatten().collect();
        ids.extend(self.extra.get(plain).into_iter().flatten());
        (!ids.is_empty()).then_some(ids)
    }

    /// The id of a learned word the table lacks, if it was learned.
    pub(crate) fn new_id(&self, word: &str) -> Option<u32> {
        self.new_ids.get(word).copied()
    }

    pub(crate) fn word(&self, id: u32) -> &str {
        match (id as usize).checked_sub(self.table.len()) {
            Some(i) => &self.new_words[i],
            None => self.table.word(id),
        }
    }

    fn own(&self, id: u32) -> bool {
        (id as usize) < self.table.len()
    }

    pub(crate) fn uni(&self, id: u32) -> f64 {
        let id = if id == BOS { EOS } else { id };
        let base = if self.own(id) {
            self.table.uni(id)
        } else {
            0.0
        };
        let unk = if id == UNK { self.unk_uni } else { 0 };
        base + WEIGHT * (self.uni.get(&id).copied().unwrap_or(0) + unk) as f64
    }

    pub(crate) fn bigram(&self, v: u32, w: u32) -> f64 {
        let base = if self.own(v) && self.own(w) {
            self.table.bigram(v, w)
        } else {
            0.0
        };
        let k = key2(v, w);
        base + WEIGHT * (get(&self.bi, k) + get(&self.unk_bi, k)) as f64
    }

    pub(crate) fn trigram(&self, u: u32, v: u32, w: u32) -> f64 {
        let own = self.own(u) && self.own(v) && self.own(w);
        let base = if own {
            self.table.trigram(u, v, w)
        } else {
            0.0
        };
        let k = key3(u, v, w);
        base + WEIGHT * (get(&self.tri, k) + get(&self.unk_tri, k)) as f64
    }

    pub(crate) fn total(&self) -> f64 {
        self.table.total() + WEIGHT * self.tokens as f64
    }

    pub(crate) fn segments(&self) -> f64 {
        self.uni(EOS)
    }

    /// Writes what was learned, one n-gram per line with words by spelling.
    pub fn save(&self, out: &mut impl Write) -> std::io::Result<()> {
        let name = |id: u32| match id {
            BOS => "<s>",
            EOS => "</s>",
            _ => self.word(id),
        };
        let mut lines: Vec<String> = Vec::new();
        for (&id, &c) in &self.uni {
            lines.push(format!("1\t{c}\t{}", name(id)));
        }
        let mask = u64::from(MAX_ID);
        for (&k, &c) in &self.bi {
            let (v, w) = ((k >> SHIFT) as u32, (k & mask) as u32);
            lines.push(format!("2\t{c}\t{}\t{}", name(v), name(w)));
        }
        for (&k, &c) in &self.tri {
            let (u, v, w) = (
                (k >> (2 * SHIFT)) as u32,
                ((k >> SHIFT) & mask) as u32,
                (k & mask) as u32,
            );
            lines.push(format!("3\t{c}\t{}\t{}\t{}", name(u), name(v), name(w)));
        }
        lines.sort();
        writeln!(out, "{HEADER}")?;
        for line in lines {
            writeln!(out, "{line}")?;
        }
        Ok(())
    }

    /// Reads a file written by [`Personal::save`], for this table.
    pub fn load(table: &'t Table, input: impl BufRead) -> Result<Personal<'t>, Error> {
        let mut p = Personal::new(table);
        let mut lines = input.lines();
        if lines.next().transpose()?.as_deref() != Some(HEADER) {
            return Err(Error::Format("not a personal dictionary"));
        }
        for line in lines {
            let line = line?;
            let fields: Vec<&str> = line.split('\t').collect();
            let (Some(n), Some(c)) = (fields.first(), fields.get(1)) else {
                return Err(Error::Format("bad personal dictionary line"));
            };
            let c: u64 = c
                .parse()
                .map_err(|_| Error::Format("bad count in personal dictionary"))?;
            let words = &fields[2..];
            if n.parse::<usize>().ok() != Some(words.len()) || words.is_empty() {
                return Err(Error::Format("bad personal dictionary line"));
            }
            let mut ids = Vec::with_capacity(words.len());
            for w in words {
                ids.push(match *w {
                    "<s>" => BOS,
                    "</s>" => EOS,
                    w => p
                        .intern(w)
                        .ok_or(Error::Format("too many words in personal dictionary"))?,
                });
            }
            if ids.len() > 3 {
                return Err(Error::Format("bad personal dictionary line"));
            }
            p.add(&ids, c);
        }
        Ok(p)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ToneStyle;

    fn table() -> Table {
        let path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/tiny.timsen");
        Table::open(path).unwrap()
    }

    fn learn(p: &mut Personal, text: &str) {
        let run: Vec<Option<&str>> = text.split(' ').map(Some).collect();
        p.learn(&run);
    }

    #[test]
    fn a_word_the_table_lacks_can_be_guessed() {
        let t = table();
        let mut p = Personal::new(&t);
        assert_eq!(p.restore(&["ngo", "sen"], ToneStyle::New), ["ngo", "sen"]);
        learn(&mut p, "ngó sen");
        assert_eq!(p.restore(&["Ngo", "sen"], ToneStyle::New), ["Ngó", "sen"]);
    }

    #[test]
    fn a_learned_unmarked_word_competes_with_the_tables_spellings() {
        let t = table();
        let mut p = Personal::new(&t);
        assert_ne!(p.restore(&["let", "go"], ToneStyle::New)[1], "go");
        learn(&mut p, "let go");
        assert_eq!(p.restore(&["let", "go"], ToneStyle::New)[1], "go");
        assert_eq!(p.restore(&["toi", "go", "phim"], ToneStyle::New)[1], "gõ");
    }

    #[test]
    fn a_new_context_word_shares_what_other_new_words_were_followed_by() {
        let t = table();
        let mut p = Personal::new(&t);
        for _ in 0..3 {
            learn(&mut p, "gõ");
        }
        learn(&mut p, "abc gỗ");
        learn(&mut p, "def gỗ");
        learn(&mut p, "ghi");
        assert_eq!(p.restore(&["ghi", "go"], ToneStyle::New), ["ghi", "gỗ"]);
    }

    #[test]
    fn nothing_is_learned_across_an_unknown_word() {
        let t = table();
        let mut p = Personal::new(&t);
        p.learn(&[Some("nhà"), None, Some("gõ")]);
        let (nha, go) = (p.intern("nhà").unwrap(), p.intern("gõ").unwrap());
        assert_eq!(p.uni[&nha], 1);
        assert_eq!(p.uni[&go], 1);
        assert!(p.bi.keys().all(|&k| k != key2(nha, go)));
        p.learn(&[None, None]);
        assert_eq!(p.uni[&EOS], 1);
    }

    #[test]
    fn saving_and_loading_keeps_what_was_learned() {
        let t = table();
        let mut p = Personal::new(&t);
        learn(&mut p, "nhà ta có gõ quý");
        learn(&mut p, "ngó sen");
        let mut file = Vec::new();
        p.save(&mut file).unwrap();
        let text = String::from_utf8(file.clone()).unwrap();
        assert!(text.contains("\tngó\tsen") && text.starts_with(HEADER));
        let q = Personal::load(&t, file.as_slice()).unwrap();
        for run in [&["nha", "ta", "co", "go", "quy"][..], &["ngo", "sen"]] {
            assert_eq!(
                q.restore(run, ToneStyle::New),
                p.restore(run, ToneStyle::New)
            );
        }
        assert_eq!(q.total(), p.total());
    }

    #[test]
    fn the_total_adds_learned_known_words_and_run_ends() {
        let t = table();
        let mut p = Personal::new(&t);
        learn(&mut p, "nhà ta");
        learn(&mut p, "ngó");
        assert_eq!(p.total(), t.total() + WEIGHT * (3.0 + 1.0));
    }

    #[test]
    fn clear_forgets_everything() {
        let t = table();
        let mut p = Personal::new(&t);
        learn(&mut p, "ngó sen");
        p.clear();
        assert!(p.is_empty());
        assert_eq!(p.restore(&["ngo"], ToneStyle::New), ["ngo"]);
    }

    #[test]
    fn a_broken_file_is_an_error() {
        let t = table();
        for text in [
            "",
            "something else\n",
            "timsen-personal 1\n2\t1\tgõ\n",
            "timsen-personal 1\n1\tx\tgõ\n",
        ] {
            assert!(Personal::load(&t, text.as_bytes()).is_err(), "{text:?}");
        }
    }
}
