//! Accuracy and speed of restoring while typing.
//!
//! usage: cargo run --release --example typing_eval TABLE RUNS TRUTH
//! RUNS and TRUTH come from `research.crosscheck`. Each run is typed one syllable at a time; after
//! each syllable the whole guess is asked for and timed. "Fixed after k" scores each word as it was
//! shown once k more syllables had been typed (the end of the run counts as known).

use std::time::{Duration, Instant};

use timsen::{Table, ToneStyle, Typing};

const WINDOWS: usize = 5;

fn read_runs(path: &str) -> std::io::Result<Vec<Vec<String>>> {
    let text = std::fs::read_to_string(path)?;
    Ok(text
        .lines()
        .map(|l| l.split(' ').map(str::to_string).collect())
        .collect())
}

fn percentile(sorted: &[Duration], p: f64) -> f64 {
    let i = ((sorted.len() - 1) as f64 * p).round() as usize;
    sorted[i].as_secs_f64() * 1e3
}

/// How many times word j changes after it is first shown, including the final restoration.
fn changes(shown: &[Vec<String>], last: &[String], j: usize) -> usize {
    let mut seen = &shown[j][j];
    let mut n = 0;
    for word in shown[j + 1..].iter().map(|g| &g[j]).chain([&last[j]]) {
        if word != seen {
            n += 1;
            seen = word;
        }
    }
    n
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let [table, runs, truth] = &args[..] else {
        return Err("usage: typing_eval TABLE RUNS TRUTH".into());
    };
    let start = Instant::now();
    let table = Table::open(table)?;
    let open = start.elapsed();
    let (runs, truth) = (read_runs(runs)?, read_runs(truth)?);
    let (mut words, mut right, mut whole) = (0, [0usize; WINDOWS], 0);
    let (mut changed, mut total_changes) = (0, 0);
    let mut times = Vec::new();
    for (run, truth) in runs.iter().zip(&truth) {
        let mut typing = Typing::new(&table);
        let mut shown = Vec::with_capacity(run.len());
        for syllable in run {
            let t = Instant::now();
            typing.push(syllable);
            let guess = typing.guess(ToneStyle::New);
            times.push(t.elapsed());
            shown.push(guess);
        }
        let last = typing.finish(ToneStyle::New);
        for j in 0..run.len() {
            words += 1;
            whole += usize::from(last[j] == truth[j]);
            for (k, r) in right.iter_mut().enumerate() {
                let word = shown.get(j + k).map_or(&last[j], |g| &g[j]);
                *r += usize::from(*word == truth[j]);
            }
            let c = changes(&shown, &last, j);
            changed += usize::from(c > 0);
            total_changes += c;
        }
    }
    let first = times[0];
    times.sort();
    let pct = |n: usize| 100.0 * n as f64 / words as f64;
    println!("words {words}  whole run {:.2}%", pct(whole));
    for (k, r) in right.iter().enumerate() {
        println!("  fixed after {k}: {:.2}%", pct(*r));
    }
    println!(
        "  changed after shown: {:.2}% of words, {total_changes} changes",
        pct(changed)
    );
    let ms = |d: Duration| d.as_secs_f64() * 1e3;
    println!(
        "  open {:.3} ms, first syllable {:.3} ms",
        ms(open),
        ms(first)
    );
    println!(
        "  per syllable (ms, {} samples): p50 {:.3} p95 {:.3} p99 {:.3} max {:.3}",
        times.len(),
        percentile(&times, 0.5),
        percentile(&times, 0.95),
        percentile(&times, 0.99),
        percentile(&times, 1.0)
    );
    Ok(())
}
