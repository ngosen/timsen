//! What an input method pays for Đoán dấu, each part timed alone: opening the table, loading and
//! saving the personal file, a key at word end in runs of a given length, and memory for the table
//! and its peak while a second copy is opened in its place, as on a table update.
//!
//! usage: cargo run --release --example latency TABLE RUNS LEARNED DIR LENGTH...
//! RUNS: unmarked runs from `research.crosscheck`, one per line; their syllables are joined into
//! runs of exactly each LENGTH. LEARNED: text with marks, learned into a personal dictionary kept in
//! DIR. A key is what Ngó Sen does when a word ends: `Run::push`, `Run::change` and `Run::apply`.
//! Linux only, since memory is read from `/proc/self/status`.

use std::path::Path;
use std::sync::Arc;
use std::time::{Duration, Instant};

use timsen::{Dictionary, Reach, Run, Table, ToneStyle};

fn status_mb(field: &str) -> f64 {
    let status = std::fs::read_to_string("/proc/self/status").unwrap_or_default();
    let kb = status
        .lines()
        .find_map(|l| l.strip_prefix(field))
        .and_then(|v| v.trim().trim_end_matches(" kB").trim().parse::<f64>().ok())
        .unwrap_or(f64::NAN);
    kb / 1024.0
}

fn ms(d: Duration) -> f64 {
    d.as_secs_f64() * 1e3
}

fn timed<T>(f: impl FnOnce() -> T) -> (T, f64) {
    let start = Instant::now();
    let out = f();
    (out, ms(start.elapsed()))
}

fn percentiles(keys: &mut [Duration]) -> String {
    keys.sort();
    let at = |p: f64| ms(keys[((keys.len() - 1) as f64 * p).round() as usize]);
    format!(
        "{} keys: p50 {:.3} p95 {:.3} p99 {:.3} max {:.3} ms",
        keys.len(),
        at(0.5),
        at(0.95),
        at(0.99),
        at(1.0)
    )
}

/// Learns every line of `learned` and saves it to `dir`, then opens it again from there.
fn personal(table: &Arc<Table>, learned: &str, dir: &Path) -> Dictionary {
    let path = dir.join("personal.txt");
    let _ = std::fs::remove_file(&path);
    let mut d = Dictionary::open(Arc::clone(table), &path);
    let text = std::fs::read_to_string(learned).expect("cannot read learned text");
    let mut tokens = 0;
    for line in text.lines() {
        let run: Vec<Option<&str>> = line.split_whitespace().map(Some).collect();
        tokens += run.len();
        d.learn(&run);
    }
    let (saved, save_ms) = timed(|| {
        let job = d.begin_save().expect("a save is owed");
        let written = job.write();
        d.finish_save(job, written)
    });
    assert!(saved.expect("cannot save"));
    let bytes = std::fs::metadata(&path).unwrap().len();
    let (d, load_ms) = timed(|| Dictionary::open(Arc::clone(table), &path));
    assert!(d.problem().is_none());
    println!(
        "personal: {tokens} words learned, file {:.1} MB, save {save_ms:.1} ms, load {load_ms:.1} ms",
        bytes as f64 / 1e6
    );
    d
}

/// Times each word end in runs of `length` syllables; returns the keys and a hash of the text shown
/// at the end, so two builds can be checked to restore alike.
fn keys(d: &Dictionary, syllables: &[&str], length: usize) -> (Vec<Duration>, Vec<Duration>, u64) {
    let (mut all, mut late) = (Vec::new(), Vec::new());
    let mut checksum = 0xcbf2_9ce4_8422_2325u64;
    for chunk in syllables.chunks_exact(length) {
        let mut run = Run::new(d.typing(), 0.99);
        for (i, s) in chunk.iter().enumerate() {
            let start = Instant::now();
            run.push(s);
            if let Some(c) = run.change(false, Reach::Run, ToneStyle::New) {
                assert!(run.apply(&c));
            }
            let took = start.elapsed();
            all.push(took);
            if i >= length * 9 / 10 {
                late.push(took);
            }
        }
        if let Some(c) = run.change(true, Reach::Run, ToneStyle::New) {
            assert!(run.apply(&c));
        }
        // FNV-1a over the shown text: a count of letters would not see marks change.
        for b in run.shown().join(" ").bytes() {
            checksum = (checksum ^ u64::from(b)).wrapping_mul(0x100_0000_01b3);
        }
    }
    (all, late, checksum)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let [_, table_path, runs, learned, dir, lengths @ ..] = args.as_slice() else {
        eprintln!("usage: latency TABLE RUNS LEARNED DIR LENGTH...");
        std::process::exit(2);
    };
    let before = status_mb("VmRSS:");
    let (table, open_ms) = timed(|| Arc::new(Table::open(table_path).expect("cannot open table")));
    println!(
        "open {open_ms:.1} ms, resident {:.1} MB more",
        status_mb("VmRSS:") - before
    );
    let d = personal(&table, learned, Path::new(dir));
    let text = std::fs::read_to_string(runs).expect("cannot read runs");
    let syllables: Vec<&str> = text.split_whitespace().collect();
    for length in lengths {
        let length: usize = length.parse().expect("LENGTH is a number");
        let (mut all, mut late, checksum) = keys(&d, &syllables, length);
        println!(
            "runs of {length}: {}, hash {checksum:016x}",
            percentiles(&mut all)
        );
        println!("  last tenth of each run: {}", percentiles(&mut late));
    }
    let typed = status_mb("VmRSS:");
    // Resets the peak, so it is the peak of the reload and not of learning above.
    std::fs::write("/proc/self/clear_refs", "5").expect("cannot reset the peak");
    assert!(status_mb("VmHWM:") <= typed + 1.0, "the peak did not reset");
    let (again, reopen_ms) = timed(|| Arc::new(Table::open(table_path).unwrap()));
    // The dictionary is read again for the new table, then the old pair goes.
    let new = Dictionary::open(Arc::clone(&again), Path::new(dir).join("personal.txt"));
    drop((d, table));
    println!(
        "resident after typing {:.1} MB; reopening {reopen_ms:.1} ms, peak {:.1} MB, then {:.1} MB",
        typed - before,
        status_mb("VmHWM:") - before,
        status_mb("VmRSS:") - before
    );
    drop(new);
}
