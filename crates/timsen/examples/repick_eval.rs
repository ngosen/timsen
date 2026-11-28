//! Where a key that picks a changed phrase again would find the right reading.
//!
//! usage: cargo run --release --example repick_eval TABLE RUNS TRUTH
//! RUNS and TRUTH come from `research.crosscheck`. Each run is typed twice: every word without
//! marks, and every word as written, so only words written without marks are guessed. The phrase
//! the key picks is the changed words (shown other than typed) among the last K words of the run.
//! After the last word, with the run still open, a run with a wrong word is scored: whether every
//! wrong word is in that phrase, and if so where the right reading of the phrase is among
//! `Typing::readings` (first press, among the next two, the two after) or only as typed. Also scored
//! for each wrong word: whether it was wrong while still among the last K words, and whether no later
//! changed word has its letters, so typing it again could point at it.

use timsen::{Table, ToneStyle, Typing};

const SPANS: [usize; 2] = [2, 3];
const TOP: usize = 6;

fn read_runs(path: &str) -> std::io::Result<Vec<Vec<String>>> {
    let text = std::fs::read_to_string(path)?;
    Ok(text
        .lines()
        .map(|l| l.split(' ').map(str::to_string).collect())
        .collect())
}

/// Counts for one way of typing.
#[derive(Default)]
struct Tally {
    words: usize,
    changed: usize,
    wrong: usize,
    runs_wrong: usize,
    /// Per span length: runs with every wrong word in the phrase, and where its right reading is:
    /// first press, second or third, fourth or fifth, only as typed, nowhere.
    inside: [usize; 2],
    at: [[usize; 5]; 2],
    /// Per span length: wrong words that were wrong while among the last K words.
    in_reach: [usize; 2],
    /// Wrong words a word typed again would point at.
    retyped: usize,
}

impl Tally {
    fn add(&mut self, table: &Table, typed: &[String], plain: &[String], truth: &[String]) {
        let mut typing = Typing::new(table);
        let mut guesses = Vec::with_capacity(typed.len());
        for word in typed {
            typing.push(word);
            guesses.push(typing.guess(ToneStyle::New));
        }
        let n = typed.len();
        let shown = &guesses[n - 1];
        let changed: Vec<bool> = shown.iter().zip(typed).map(|(s, t)| s != t).collect();
        let wrong: Vec<usize> = (0..n).filter(|&j| shown[j] != truth[j]).collect();
        self.words += n;
        self.changed += changed.iter().filter(|&&c| c).count();
        self.wrong += wrong.len();
        if wrong.is_empty() {
            return;
        }
        self.runs_wrong += 1;
        for (s, &k) in SPANS.iter().enumerate() {
            let span: Vec<usize> = (n.saturating_sub(k)..n).filter(|&j| changed[j]).collect();
            for &j in &wrong {
                let last = (j + k).min(n);
                self.in_reach[s] += usize::from((j..last).any(|t| guesses[t][j] != truth[j]));
            }
            if !wrong.iter().all(|j| span.contains(j)) {
                continue;
            }
            self.inside[s] += 1;
            let readings = typing.readings(&span, TOP, false, ToneStyle::New);
            let bucket = match readings.iter().position(|r| r == truth) {
                Some(1) => 0,
                Some(2..=3) => 1,
                Some(4..=5) => 2,
                _ if span.iter().all(|&j| typed[j] == truth[j]) => 3,
                _ => 4,
            };
            self.at[s][bucket] += 1;
        }
        for &j in &wrong {
            let alone = !(j + 1..n).any(|t| changed[t] && plain[t] == plain[j]);
            self.retyped += usize::from(changed[j] && alone);
        }
    }

    fn print(&self, name: &str) {
        let pct = |n: usize, d: usize| 100.0 * n as f64 / d.max(1) as f64;
        println!(
            "{name}: {} words, {:.2}% changed, {:.2}% wrong ({}), {} runs with a wrong word",
            self.words,
            pct(self.changed, self.words),
            pct(self.wrong, self.words),
            self.wrong,
            self.runs_wrong,
        );
        for (s, k) in SPANS.iter().enumerate() {
            let [a, b, c, d, e] = self.at[s].map(|n| pct(n, self.inside[s]));
            println!(
                "  last {k}: every wrong word in the phrase for {:.1}% of those runs; right reading: first press {a:.1}%, 2-3 {b:.1}%, 4-5 {c:.1}%, only as typed {d:.1}%, nowhere {e:.1}%",
                pct(self.inside[s], self.runs_wrong),
            );
            println!(
                "    wrong while among the last {k}: {:.1}% of wrong words",
                pct(self.in_reach[s], self.wrong)
            );
        }
        println!(
            "  typed again, points at {:.1}% of wrong words",
            pct(self.retyped, self.wrong)
        );
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let [table, runs, truth] = &args[..] else {
        return Err("usage: repick_eval TABLE RUNS TRUTH".into());
    };
    let table = Table::open(table)?;
    let (runs, truth) = (read_runs(runs)?, read_runs(truth)?);
    let (mut plain, mut written) = (Tally::default(), Tally::default());
    for (run, truth) in runs.iter().zip(&truth) {
        plain.add(&table, run, run, truth);
        written.add(&table, truth, run, truth);
    }
    plain.print("typed without marks");
    written.print("typed as written");
    Ok(())
}
