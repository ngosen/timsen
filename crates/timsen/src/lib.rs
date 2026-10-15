//! Restores Vietnamese diacritics from a syllable n-gram table: `toi da go phim` → `tôi đã gõ phím`.
//!
//! The table is built by `research.table`. Restoration matches `research.model` exactly on the same
//! table: 3-grams with stupid backoff, and a Viterbi search over the whole run. [`Typing`] restores a
//! run while it is typed.

mod table;
mod tone;
mod typing;

pub use table::{Error, Table};
pub use tone::ToneStyle;
pub use typing::{Choices, Typing};

use table::BOS;

/// Log weight of each step down to a shorter n-gram (stupid backoff, 0.4).
fn backoff() -> f64 {
    0.4f64.ln()
}

impl Table {
    /// Restores a run of syllables typed without marks, such as the words between two punctuation
    /// marks. Each output word keeps the capitalization of its input; words the table does not know
    /// come back as typed.
    pub fn restore(&self, run: &[&str], style: ToneStyle) -> Vec<String> {
        let mut typing = Typing::new(self);
        for syllable in run {
            typing.push(syllable);
        }
        typing.finish(style)
    }

    /// Log score of `w` after `u v`, as `Model.logp` computes it.
    pub(crate) fn logp(&self, u: u32, v: u32, w: u32) -> f64 {
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
}
