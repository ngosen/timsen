//! Restores Vietnamese diacritics from a syllable n-gram table: `toi da go phim` → `tôi đã gõ phím`.
//!
//! The table is built by `research.table`. Restoration matches `research.model` exactly on the same
//! table: 3-grams with stupid backoff, and a Viterbi search over the whole run.

mod table;
mod tone;

pub use table::{Error, Table};
pub use tone::ToneStyle;

use table::{BOS, EOS, UNK};

/// Log weight of each step down to a shorter n-gram (stupid backoff, 0.4).
fn backoff() -> f64 {
    0.4f64.ln()
}

impl Table {
    /// Restores a run of syllables typed without marks, such as the words between two punctuation
    /// marks. Each output word keeps the capitalization of its input; words the table does not know
    /// come back as typed.
    pub fn restore(&self, run: &[&str], style: ToneStyle) -> Vec<String> {
        let plain: Vec<String> = run.iter().map(|w| w.to_lowercase()).collect();
        let ids = self.best_path(&plain);
        run.iter()
            .zip(&plain)
            .zip(ids)
            .map(|((typed, p), id)| {
                let word = if id == UNK { p.as_str() } else { self.word(id) };
                tone::apply_case(typed, &tone::with_style(word, style))
            })
            .collect()
    }

    /// Log score of `w` after `u v`, as `Model.logp` computes it.
    fn logp(&self, u: u32, v: u32, w: u32) -> f64 {
        let tri = self.trigram(u, v, w);
        if tri > 0.0 {
            let ctx = if u == BOS && v == BOS {
                self.segments()
            } else {
                self.bigram(u, v)
            };
            return (tri.max(1e-9) / ctx.max(1.0)).ln();
        }
        let bi = self.bigram(v, w);
        if bi > 0.0 {
            return (bi.max(1e-9) / self.uni(v).max(1.0)).ln() + backoff();
        }
        (self.uni(w).max(0.5) / self.total()).ln() + 2.0 * backoff()
    }

    /// Word ids of the best spelling of each syllable. Ties go to the earlier candidate, as numpy's
    /// argmax does, so the output matches `research.model` exactly.
    fn best_path(&self, plain: &[String]) -> Vec<u32> {
        let opts: Vec<Vec<u32>> = plain
            .iter()
            .map(|p| self.options(p).map_or_else(|| vec![UNK], |o| o.collect()))
            .collect();
        let (mut pp, mut prev) = (vec![BOS], vec![BOS]);
        // score[a * prev.len() + b]: best path ending with candidates pp[a], prev[b]
        let mut score = vec![0.0];
        let mut back: Vec<Vec<usize>> = Vec::with_capacity(opts.len());
        for o in &opts {
            let mut next = vec![f64::NEG_INFINITY; prev.len() * o.len()];
            let mut bp = vec![0; prev.len() * o.len()];
            for (b, &v) in prev.iter().enumerate() {
                for (c, &w) in o.iter().enumerate() {
                    let cell = b * o.len() + c;
                    for (a, &u) in pp.iter().enumerate() {
                        let s = score[a * prev.len() + b] + self.logp(u, v, w);
                        if a == 0 || s > next[cell] {
                            next[cell] = s;
                            bp[cell] = a;
                        }
                    }
                }
            }
            back.push(bp);
            score = next;
            pp = std::mem::replace(&mut prev, o.clone());
        }
        let (mut best, mut a, mut b) = (f64::NEG_INFINITY, 0, 0);
        for (i, &u) in pp.iter().enumerate() {
            for (j, &v) in prev.iter().enumerate() {
                let s = score[i * prev.len() + j] + self.logp(u, v, EOS);
                if (i == 0 && j == 0) || s > best {
                    (best, a, b) = (s, i, j);
                }
            }
        }
        let mut picks = vec![b, a];
        for (k, bp) in back.iter().enumerate().skip(2).rev() {
            let width = opts[k].len();
            (a, b) = (bp[a * width + b], a);
            picks.push(a);
        }
        picks.truncate(opts.len());
        picks.reverse();
        picks.iter().zip(&opts).map(|(&k, o)| o[k]).collect()
    }
}
