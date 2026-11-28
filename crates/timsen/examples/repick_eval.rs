//! Where a key that picks a changed word again would find the right spelling.
//!
//! usage: cargo run --release --example repick_eval TABLE RUNS TRUTH
//! RUNS and TRUTH come from `research.crosscheck`. Each run is typed twice: every word without
//! marks, and every word as written, so only words written without marks are guessed. After the
//! last word, with the run still open, each word shown wrong is scored: where the right spelling is
//! among the other choices or the word as typed, and how many words the key could pick come after
//! it. A word the key can pick is one shown other than typed, or only one the model is unsure of.

use timsen::{Table, ToneStyle, Typing};

const UNSURE: [f64; 2] = [0.9, 0.99];

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
    runs_one_wrong: usize,
    /// Where the right spelling is: second choice, third, only as typed, nowhere.
    at: [usize; 4],
    /// For each set of words the key can pick (changed, then unsure at each threshold): the wrong
    /// words in it, and how many picked words come after them (0, 1, 2, 3 or more).
    pickable: [usize; 3],
    back: [[usize; 4]; 3],
}

impl Tally {
    fn add(&mut self, table: &Table, typed: &[String], truth: &[String]) {
        let mut typing = Typing::new(table);
        for word in typed {
            typing.push(word);
        }
        let shown = typing.guess(ToneStyle::New);
        let choices = typing.choices(typed.len(), false, ToneStyle::New);
        let changed: Vec<bool> = shown.iter().zip(typed).map(|(s, t)| s != t).collect();
        let sets: [Vec<bool>; 3] = [
            changed.clone(),
            unsure(&changed, &choices, UNSURE[0]),
            unsure(&changed, &choices, UNSURE[1]),
        ];
        let wrong: Vec<usize> = (0..typed.len()).filter(|&j| shown[j] != truth[j]).collect();
        self.words += typed.len();
        self.changed += changed.iter().filter(|&&c| c).count();
        self.wrong += wrong.len();
        self.runs_wrong += usize::from(!wrong.is_empty());
        self.runs_one_wrong += usize::from(wrong.len() == 1);
        for &j in &wrong {
            let others = &choices[j].spellings[1..];
            let k = match others.iter().position(|s| *s == truth[j]) {
                Some(p) => p,
                None if typed[j] == truth[j] => 2,
                None => 3,
            };
            self.at[k] += 1;
            for (s, set) in sets.iter().enumerate() {
                if set[j] {
                    self.pickable[s] += 1;
                    let after = set[j + 1..].iter().filter(|&&p| p).count();
                    self.back[s][after.min(3)] += 1;
                }
            }
        }
    }

    fn print(&self, name: &str) {
        let pct = |n: usize, d: usize| 100.0 * n as f64 / d.max(1) as f64;
        println!(
            "{name}: {} words, {:.2}% changed, {:.2}% wrong ({}); {} runs with a wrong word, {:.1}% of them one",
            self.words,
            pct(self.changed, self.words),
            pct(self.wrong, self.words),
            self.wrong,
            self.runs_wrong,
            pct(self.runs_one_wrong, self.runs_wrong),
        );
        let [a, b, c, d] = self.at.map(|n| pct(n, self.wrong));
        println!(
            "  right spelling of a wrong word: second {a:.1}%, third {b:.1}%, only as typed {c:.1}%, nowhere {d:.1}%"
        );
        for (s, label) in ["changed", "unsure < 0.90", "unsure < 0.99"]
            .iter()
            .enumerate()
        {
            let [z, o, t, m] = self.back[s].map(|n| pct(n, self.pickable[s]));
            println!(
                "  pickable as {label}: {:.1}% of wrong words; picked words after them: 0 {z:.1}%, 1 {o:.1}%, 2 {t:.1}%, 3+ {m:.1}%",
                pct(self.pickable[s], self.wrong),
            );
        }
    }
}

fn unsure(changed: &[bool], choices: &[timsen::Choices], below: f64) -> Vec<bool> {
    changed
        .iter()
        .zip(choices)
        .map(|(&c, ch)| c && ch.confidence < below)
        .collect()
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
        plain.add(&table, run, truth);
        written.add(&table, truth, truth);
    }
    plain.print("typed without marks");
    written.print("typed as written");
    Ok(())
}
