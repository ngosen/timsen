//! Restoring a run while it is typed, one syllable at a time.

use crate::table::{BOS, EOS, UNK};
use crate::{Table, ToneStyle, tone};

const START: [u32; 1] = [BOS];

/// A run being typed. Each syllable adds one step to the Viterbi lattice, so asking for the best
/// spelling after every syllable costs one step, not a new search over the whole run.
pub struct Typing<'t> {
    table: &'t Table,
    typed: Vec<String>,
    opts: Vec<Vec<u32>>,
    /// `kept[i][k]`: the text candidate k of syllable i stands for when the user typed it that way,
    /// or `None` when it is a guess spelled from the table.
    kept: Vec<Vec<Option<String>>>,
    /// `scores[i][a * opts[i].len() + b]`: best path through syllable i ending with candidate a of
    /// syllable i - 1 and candidate b of syllable i.
    scores: Vec<Vec<f64>>,
    /// `back[i]`, same shape: the candidate of syllable i - 2 on that path.
    back: Vec<Vec<usize>>,
}

impl<'t> Typing<'t> {
    pub fn new(table: &'t Table) -> Typing<'t> {
        Typing {
            table,
            typed: Vec::new(),
            opts: Vec::new(),
            kept: Vec::new(),
            scores: Vec::new(),
            back: Vec::new(),
        }
    }

    /// Adds the next syllable. One typed without marks is guessed; one typed with marks is kept as
    /// typed and only serves as context.
    pub fn push(&mut self, syllable: &str) {
        let plain = syllable.to_lowercase();
        if tone::strip(&plain) != plain {
            return self.push_kept(syllable, &[syllable]);
        }
        let o: Vec<u32> = self
            .table
            .options(&plain)
            .map_or_else(|| vec![UNK], |o| o.collect());
        let kept = vec![None; o.len()];
        self.push_options(syllable, o, kept);
    }

    /// Adds a word the input method could read two ways: as it interpreted the keys (`tét`) and as
    /// the raw letters (`test`). Both are kept as typed; the context chooses, and an equal score
    /// keeps the interpreted one. Raw letters the table does not know are never chosen: unknown
    /// words share one pooled count, which would let any string of keys outscore a real word.
    pub fn push_either(&mut self, interpreted: &str, raw: &str) {
        if interpreted.to_lowercase() == raw.to_lowercase() || self.id_of(raw) == UNK {
            return self.push_kept(interpreted, &[interpreted]);
        }
        self.push_kept(interpreted, &[interpreted, raw]);
    }

    fn push_kept(&mut self, typed: &str, readings: &[&str]) {
        let o = readings.iter().map(|r| self.id_of(r)).collect();
        let kept = readings.iter().map(|r| Some(r.to_string())).collect();
        self.push_options(typed, o, kept);
    }

    /// The table's id for a word as typed, in either tone placement, or `UNK`.
    fn id_of(&self, word: &str) -> u32 {
        let word = tone::to_new(&word.to_lowercase());
        self.table
            .options(&tone::strip(&word))
            .and_then(|mut o| o.find(|&id| self.table.word(id) == word))
            .unwrap_or(UNK)
    }

    fn push_options(&mut self, typed: &str, o: Vec<u32>, kept: Vec<Option<String>>) {
        let n = self.opts.len();
        let (pp, prev) = (self.opts_at(n, 2), self.opts_at(n, 1));
        let score: &[f64] = if n == 0 { &[0.0] } else { &self.scores[n - 1] };
        let mut next = vec![f64::NEG_INFINITY; prev.len() * o.len()];
        let mut bp = vec![0; prev.len() * o.len()];
        for (b, &v) in prev.iter().enumerate() {
            for (c, &w) in o.iter().enumerate() {
                let cell = b * o.len() + c;
                for (a, &u) in pp.iter().enumerate() {
                    let s = score[a * prev.len() + b] + self.table.logp(u, v, w);
                    // Strictly greater keeps the first best, as numpy's argmax does.
                    if a == 0 || s > next[cell] {
                        next[cell] = s;
                        bp[cell] = a;
                    }
                }
            }
        }
        self.typed.push(typed.to_string());
        self.opts.push(o);
        self.kept.push(kept);
        self.scores.push(next);
        self.back.push(bp);
    }

    /// Removes the last syllable, as backspace over a whole syllable would.
    pub fn pop(&mut self) {
        self.typed.pop();
        self.opts.pop();
        self.kept.pop();
        self.scores.pop();
        self.back.pop();
    }

    pub fn len(&self) -> usize {
        self.typed.len()
    }

    pub fn is_empty(&self) -> bool {
        self.typed.is_empty()
    }

    /// Best spelling of every syllable so far, for a run that may still go on. Earlier words can
    /// change as later ones arrive.
    pub fn guess(&self, style: ToneStyle) -> Vec<String> {
        self.spell(&self.best_path(false), style)
    }

    /// Best spelling of the run once it has ended; the same as [`Table::restore`].
    pub fn finish(&self, style: ToneStyle) -> Vec<String> {
        self.spell(&self.best_path(true), style)
    }

    /// Candidates of syllable `n - back`, or `<s>` before the run.
    fn opts_at(&self, n: usize, back: usize) -> &[u32] {
        if n >= back {
            &self.opts[n - back]
        } else {
            &START
        }
    }

    fn best_path(&self, ended: bool) -> Vec<usize> {
        let n = self.opts.len();
        if n == 0 {
            return Vec::new();
        }
        let (pp, prev, score) = (self.opts_at(n, 2), self.opts_at(n, 1), &self.scores[n - 1]);
        let (mut best, mut a, mut b) = (f64::NEG_INFINITY, 0, 0);
        for (i, &u) in pp.iter().enumerate() {
            for (j, &v) in prev.iter().enumerate() {
                let end = if ended {
                    self.table.logp(u, v, EOS)
                } else {
                    0.0
                };
                let s = score[i * prev.len() + j] + end;
                if (i == 0 && j == 0) || s > best {
                    (best, a, b) = (s, i, j);
                }
            }
        }
        let mut picks = vec![b, a];
        for k in (2..n).rev() {
            (a, b) = (self.back[k][a * self.opts[k].len() + b], a);
            picks.push(a);
        }
        picks.truncate(n);
        picks.reverse();
        picks
    }

    fn spell(&self, picks: &[usize], style: ToneStyle) -> Vec<String> {
        picks
            .iter()
            .enumerate()
            .map(|(i, &k)| self.spell_one(i, k, style))
            .collect()
    }

    /// Candidate k of syllable i, spelled for output.
    fn spell_one(&self, i: usize, k: usize, style: ToneStyle) -> String {
        if let Some(text) = &self.kept[i][k] {
            return text.clone();
        }
        let (id, typed) = (self.opts[i][k], &self.typed[i]);
        if id == UNK {
            return typed.clone();
        }
        tone::apply_case(typed, &tone::with_style(self.table.word(id), style))
    }

    /// Spellings of each of the last `last` syllables, best first, with how sure the model is of the
    /// best one. `ended` says whether the run is over, as for [`Typing::finish`].
    pub fn choices(&self, last: usize, ended: bool, style: ToneStyle) -> Vec<Choices> {
        let from = self.opts.len().saturating_sub(last);
        self.max_marginals(from, ended)
            .iter()
            .enumerate()
            .map(|(j, mm)| {
                let i = from + j;
                let mut order: Vec<usize> = (0..mm.len()).collect();
                order.sort_by(|&x, &y| mm[y].total_cmp(&mm[x]));
                let top = mm[order[0]];
                let mass: f64 = mm.iter().map(|&m| (m - top).exp()).sum();
                Choices {
                    spellings: order
                        .iter()
                        .take(3)
                        .map(|&k| self.spell_one(i, k, style))
                        .collect(),
                    confidence: 1.0 / mass,
                }
            })
            .collect()
    }

    /// For syllables `from..`, the score of the best path through each of their candidates. A
    /// backward pass over those syllables meets the stored forward scores.
    fn max_marginals(&self, from: usize, ended: bool) -> Vec<Vec<f64>> {
        let n = self.opts.len();
        if from >= n {
            return Vec::new();
        }
        let (pp, prev) = (self.opts_at(n, 2), self.opts_at(n, 1));
        // beta[a * cur.len() + b]: best score of the rest of the run after candidates a, b
        let mut beta: Vec<f64> = (0..pp.len() * prev.len())
            .map(|c| {
                if ended {
                    self.table
                        .logp(pp[c / prev.len()], prev[c % prev.len()], EOS)
                } else {
                    0.0
                }
            })
            .collect();
        let mut out = Vec::with_capacity(n - from);
        for i in (from..n).rev() {
            let (left, cur) = (self.opts_at(i, 1), &self.opts[i]);
            let width = cur.len();
            out.push(
                (0..width)
                    .map(|b| {
                        (0..left.len())
                            .map(|a| self.scores[i][a * width + b] + beta[a * width + b])
                            .fold(f64::NEG_INFINITY, f64::max)
                    })
                    .collect(),
            );
            if i == from {
                break;
            }
            let left2 = self.opts_at(i, 2);
            let mut next = vec![f64::NEG_INFINITY; left2.len() * left.len()];
            for (x, &u) in left2.iter().enumerate() {
                for (a, &v) in left.iter().enumerate() {
                    for (b, &w) in cur.iter().enumerate() {
                        let s = self.table.logp(u, v, w) + beta[a * width + b];
                        let cell = &mut next[x * left.len() + a];
                        *cell = cell.max(s);
                    }
                }
            }
            beta = next;
        }
        out.reverse();
        out
    }
}

/// The spellings of one syllable, best first (at most three), and the model's confidence in the
/// first: its share of the probability over all spellings, each scored by its best path.
#[derive(Clone, Debug, PartialEq)]
pub struct Choices {
    pub spellings: Vec<String>,
    pub confidence: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn table() -> Table {
        let path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/tiny.timsen");
        Table::open(path).unwrap()
    }

    fn path_score(t: &Table, path: &[u32], ended: bool) -> f64 {
        let mut ctx = (BOS, BOS);
        let mut s = 0.0;
        for &w in path {
            s += t.logp(ctx.0, ctx.1, w);
            ctx = (ctx.1, w);
        }
        if ended {
            s + t.logp(ctx.0, ctx.1, EOS)
        } else {
            s
        }
    }

    /// Best score over every combination of candidates, for checking the lattice. Paths are not
    /// compared because equal scores may break either way.
    fn brute_force(t: &Table, opts: &[Vec<u32>], ended: bool) -> f64 {
        let mut best = f64::NEG_INFINITY;
        let mut idx = vec![0; opts.len()];
        loop {
            let path: Vec<u32> = idx.iter().zip(opts).map(|(&k, o)| o[k]).collect();
            best = best.max(path_score(t, &path, ended));
            let mut i = opts.len();
            loop {
                if i == 0 {
                    return best;
                }
                i -= 1;
                idx[i] += 1;
                if idx[i] < opts[i].len() {
                    break;
                }
                idx[i] = 0;
            }
        }
    }

    #[test]
    fn every_prefix_matches_exhaustive_search() {
        let t = table();
        let runs = std::fs::read_to_string(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/tests/fixtures/tiny.runs"
        ));
        for run in runs.unwrap().lines() {
            let mut typing = Typing::new(&t);
            for w in run.split(' ') {
                typing.push(w);
                for ended in [false, true] {
                    let ids: Vec<u32> = typing
                        .best_path(ended)
                        .iter()
                        .enumerate()
                        .map(|(i, &k)| typing.opts[i][k])
                        .collect();
                    let got = path_score(&t, &ids, ended);
                    assert_eq!(
                        got,
                        brute_force(&t, &typing.opts, ended),
                        "{run} ended={ended}"
                    );
                }
            }
        }
    }

    /// Best score over all paths that put candidate k at syllable i.
    fn brute_marginal(t: &Table, opts: &[Vec<u32>], i: usize, k: usize, ended: bool) -> f64 {
        let mut fixed = opts.to_vec();
        fixed[i] = vec![opts[i][k]];
        brute_force(t, &fixed, ended)
    }

    #[test]
    fn choices_match_exhaustive_search() {
        let t = table();
        let runs = std::fs::read_to_string(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/tests/fixtures/tiny.runs"
        ));
        for run in runs.unwrap().lines() {
            let mut typing = Typing::new(&t);
            for w in run.split(' ') {
                typing.push(w);
                for ended in [false, true] {
                    let from = typing.len().saturating_sub(3);
                    for (j, mm) in typing.max_marginals(from, ended).iter().enumerate() {
                        for (k, &m) in mm.iter().enumerate() {
                            let want = brute_marginal(&t, &typing.opts, from + j, k, ended);
                            assert!(
                                (m - want).abs() < 1e-9,
                                "{run} ended={ended} syllable {} candidate {k}",
                                from + j
                            );
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn choices_lead_with_the_guess() {
        let t = table();
        let mut typing = Typing::new(&t);
        for w in ["nguoi", "ta", "co", "go", "cua"] {
            typing.push(w);
        }
        let choices = typing.choices(3, false, ToneStyle::New);
        assert_eq!(choices.len(), 3);
        let guess = typing.guess(ToneStyle::New);
        for (c, g) in choices.iter().zip(&guess[2..]) {
            assert_eq!(&c.spellings[0], g);
            assert!(c.confidence > 0.0 && c.confidence <= 1.0);
        }
        assert!(choices[1].spellings.contains(&"gỗ".to_string()));
    }

    #[test]
    fn a_word_with_one_spelling_is_certain() {
        let t = table();
        let mut typing = Typing::new(&t);
        for w in ["nha", "xyzzy"] {
            typing.push(w);
        }
        let last = &typing.choices(1, true, ToneStyle::New)[0];
        assert_eq!(last.spellings, ["xyzzy"]);
        assert_eq!(last.confidence, 1.0);
    }

    #[test]
    fn pop_undoes_push() {
        let t = table();
        let mut typing = Typing::new(&t);
        for w in ["nha", "ta", "co", "go"] {
            typing.push(w);
        }
        let before = typing.guess(ToneStyle::New);
        typing.push("quy");
        typing.pop();
        assert_eq!(typing.guess(ToneStyle::New), before);
        assert_eq!(typing.len(), 4);
    }

    #[test]
    fn an_open_run_and_an_ended_one_can_differ() {
        let t = table();
        let mut typing = Typing::new(&t);
        for w in ["ban", "thich", "go"] {
            typing.push(w);
        }
        assert_eq!(typing.guess(ToneStyle::New)[2], "gõ");
        assert_eq!(typing.finish(ToneStyle::New)[2], "gỗ");
    }

    #[test]
    fn a_later_word_changes_an_earlier_guess() {
        let t = table();
        let mut typing = Typing::new(&t);
        for w in ["nguoi", "ta", "co", "go"] {
            typing.push(w);
        }
        typing.push("quy");
        assert_eq!(typing.guess(ToneStyle::New)[3], "gỗ");
        typing.pop();
        typing.push("cua");
        assert_eq!(typing.guess(ToneStyle::New)[3], "gõ");
    }

    #[test]
    fn a_marked_word_is_kept_and_steers_its_neighbours() {
        let t = table();
        for (last, want) in [("quý", "gỗ"), ("cửa", "gõ")] {
            let mut typing = Typing::new(&t);
            for w in ["nguoi", "ta", "co", "go", last] {
                typing.push(w);
            }
            assert_eq!(typing.finish(ToneStyle::New)[3..], [want, last]);
        }
    }

    #[test]
    fn a_marked_word_is_found_in_either_tone_placement() {
        let t = table();
        let mut typing = Typing::new(&t);
        typing.push("Hòa");
        assert_eq!(typing.guess(ToneStyle::New), ["Hòa"]);
        assert_ne!(typing.opts[0][0], UNK);
        assert_eq!(typing.id_of("hoà"), typing.opts[0][0]);
    }

    #[test]
    fn an_unknown_raw_reading_never_wins() {
        let t = table();
        let mut typing = Typing::new(&t);
        for w in ["nhà", "ta", "có"] {
            typing.push(w);
        }
        typing.push_either("gỗ", "goox");
        typing.push_either("quý", "quys");
        // Unknown words share one pooled count, which on a real table outscores most real words.
        let ids = [[typing.id_of("gỗ")], [typing.id_of("quý")]];
        assert_eq!(typing.opts[3..], ids);
        assert_eq!(typing.finish(ToneStyle::New)[3..], ["gỗ", "quý"]);
    }

    #[test]
    fn either_reading_follows_the_context() {
        let t = table();
        let mut typing = Typing::new(&t);
        typing.push("mở");
        typing.push_either("fìle", "file");
        typing.push("code");
        assert_eq!(typing.finish(ToneStyle::New), ["mở", "file", "code"]);
        typing.pop();
        typing.pop();
        typing.push_either("tét", "test");
        assert_eq!(typing.finish(ToneStyle::New)[1], "tét");
    }
}
