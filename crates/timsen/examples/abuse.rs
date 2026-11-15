//! Feeds the crate damaged tables, damaged personal files, odd text and calls in any order, built
//! the way Ngó Sen builds it (`panic = "abort"`), where `cargo test` would catch a panic instead.
//! Each case asserts its result; any panic aborts the process, so a run that exits 0 saw none.
//!
//!     scripts/abuse.sh                  # release profile, then again with overflow checks
//!     cargo run --example abuse -- --control   # panics on purpose: must not exit 0

use std::fs;
use std::path::PathBuf;
use std::sync::Arc;

use timsen::{Change, Dictionary, Personal, Reach, Run, Table, ToneStyle, Typing};

const FIXTURE: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/tiny.timsen");
const LEARNED: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/tiny.learned");
const RUNS: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/tiny.runs");

/// Text an input method could hand over: empty, spaces, controls, combining marks, letters whose
/// case changes their length, emoji, and a very long word.
const ODD: [&str; 16] = [
    "",
    " ",
    "\t",
    "\n",
    "\0",
    "\u{301}",
    "a\u{301}",
    "İ",
    "ß",
    "ǅ",
    "ﬁ",
    "😀",
    "Đ",
    "<s>",
    "</s>",
    "ĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐĐ",
];
const WORDS: [&str; 10] = [
    "toi", "go", "phim", "nha", "ta", "co", "quy", "Ngo", "SEN", "gõ",
];

/// xorshift64*: the same cases on every run, with no dependency.
struct Rng(u64);

impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        self.0.wrapping_mul(0x2545_f491_4f6c_dd1d)
    }

    fn below(&mut self, n: usize) -> usize {
        (self.next() % n.max(1) as u64) as usize
    }

    fn word(&mut self) -> &'static str {
        if self.below(3) == 0 {
            ODD[self.below(ODD.len())]
        } else {
            WORDS[self.below(WORDS.len())]
        }
    }
}

fn main() {
    if std::env::args().any(|a| a == "--control") {
        panic!("control case: this run must not exit 0");
    }
    let mut rng = Rng(0x9e37_79b9_7f4a_7c15);
    let fixture = fs::read(FIXTURE).unwrap();
    let table = Arc::new(Table::from_bytes(fixture.clone()).unwrap());
    let mut done = 0;
    done += truncated_tables(&fixture);
    done += corrupt_tables(&fixture, &mut rng);
    done += broken_personal_files(&table, &mut rng);
    done += kept_personal_files(&table, &mut rng);
    done += calls_in_any_order(&table, &mut rng);
    println!("{done} cases, no panic");
}

/// Restores a run with every entry point; the output always has one word per input word.
fn exercise(typing: Typing, rng: &mut Rng) {
    let mut run = Run::new(typing, 0.99);
    for _ in 0..8 {
        let w = rng.word();
        if rng.below(4) == 0 {
            run.push_either(w, rng.word());
        } else {
            run.push(w);
        }
        if let Some(c) = run.change(rng.below(2) == 0, Reach::Run, ToneStyle::Old) {
            assert_eq!(c.old.len(), c.new.len());
            assert!(run.apply(&c));
        }
    }
    assert_eq!(run.shown().len(), run.len());
}

/// A table cut short is an `Error`, unless the cut only took the padding after the last section:
/// then it restores exactly like the whole table.
fn truncated_tables(fixture: &[u8]) -> usize {
    let text = fs::read_to_string(RUNS).unwrap();
    let words: Vec<&str> = text.split_whitespace().collect();
    let whole = Table::from_bytes(fixture.to_vec()).unwrap();
    let want = whole.restore(&words, ToneStyle::New);
    let mut opened = 0;
    for n in 0..fixture.len() {
        if let Ok(t) = Table::from_bytes(fixture[..n].to_vec()) {
            assert!(fixture[n..].iter().all(|&b| b == 0), "cut at {n} took data");
            assert_eq!(t.restore(&words, ToneStyle::New), want, "cut at {n}");
            opened += 1;
        }
    }
    assert!(opened < 8, "{opened} cuts opened: more than the padding");
    fixture.len()
}

fn corrupt_tables(fixture: &[u8], rng: &mut Rng) -> usize {
    let cases = 3000;
    for _ in 0..cases {
        let mut bytes = fixture.to_vec();
        for _ in 0..1 + rng.below(4) {
            let at = rng.below(bytes.len());
            bytes[at] = rng.next() as u8;
        }
        if let Ok(t) = Table::from_bytes(bytes) {
            let words = ["toi", "go", "phim", "Ngo", "", "xyz"];
            assert_eq!(t.restore(&words, ToneStyle::New).len(), words.len());
            exercise(Typing::new(&t), rng);
        }
    }
    for _ in 0..500 {
        let len = rng.below(200);
        let mut bytes: Vec<u8> = (0..len).map(|_| rng.next() as u8).collect();
        if rng.below(2) == 0 && bytes.len() >= 8 {
            bytes[..8].copy_from_slice(&fixture[..8]);
        }
        let _ = Table::from_bytes(bytes);
    }
    cases + 500
}

fn learned_file(table: &Arc<Table>) -> Vec<u8> {
    let mut d = Dictionary::new(Arc::clone(table));
    for line in fs::read_to_string(LEARNED).unwrap().lines() {
        let run: Vec<Option<&str>> = line.split(' ').map(Some).collect();
        d.learn(&run);
    }
    let mut file = Vec::new();
    d.save(&mut file).unwrap();
    file
}

/// Truncated and corrupt personal files load or give an `Error`, never a panic.
fn broken_personal_files(table: &Arc<Table>, rng: &mut Rng) -> usize {
    let file = learned_file(table);
    let mut cases = 0;
    for n in 0..file.len() {
        if let Ok(p) = Personal::load_shared(Arc::clone(table), &file[..n]) {
            exercise(Typing::with_shared_personal(Arc::new(p)), rng);
        }
        cases += 1;
    }
    for _ in 0..2000 {
        let mut bytes = file.clone();
        for _ in 0..1 + rng.below(4) {
            let at = rng.below(bytes.len());
            bytes[at] = rng.next() as u8;
        }
        if let Ok(p) = Personal::load_shared(Arc::clone(table), bytes.as_slice()) {
            exercise(Typing::with_shared_personal(Arc::new(p)), rng);
        }
        cases += 1;
    }
    cases
}

/// A personal file that does not load is left byte for byte, whatever is done with the dictionary.
fn kept_personal_files(table: &Arc<Table>, rng: &mut Rng) -> usize {
    let dir = std::env::temp_dir().join(format!("timsen-abuse-{}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir(&dir).unwrap();
    let path: PathBuf = dir.join("personal.txt");
    let file = learned_file(table);
    let mut cases = 0;
    for _ in 0..300 {
        let mut bytes = file.clone();
        let at = rng.below(bytes.len());
        bytes[at] = [0xff, b'\t', b'\n', b'x'][rng.below(4)];
        bytes.truncate(bytes.len() - rng.below(bytes.len() / 2));
        fs::write(&path, &bytes).unwrap();
        let mut d = Dictionary::open(Arc::clone(table), &path);
        if d.problem().is_none() {
            continue;
        }
        d.learn(&[Some("ngó"), Some("sen")]);
        d.clear();
        assert!(d.begin_save().is_none());
        assert!(d.reload_file().is_err());
        assert_eq!(fs::read(&path).unwrap(), bytes, "a broken file changed");
        cases += 1;
    }
    fs::remove_dir_all(&dir).unwrap();
    assert!(cases > 0, "no corrupt file failed to load");
    cases
}

fn calls_in_any_order(table: &Arc<Table>, rng: &mut Rng) -> usize {
    let cases = 20_000;
    let mut d = Dictionary::new(Arc::clone(table));
    let mut typing = Typing::shared(Arc::clone(table));
    let mut run = Run::new(d.typing(), 0.99);
    let mut pushed = 0usize;
    for _ in 0..cases {
        match rng.below(12) {
            0 => {
                typing.push(rng.word());
                pushed += 1;
            }
            1 => {
                typing.pop();
                pushed = pushed.saturating_sub(1);
            }
            2 => assert_eq!(typing.guess(ToneStyle::New).len(), pushed),
            3 => assert_eq!(typing.finish(ToneStyle::Old).len(), pushed),
            4 => {
                let last = [0, 1, 3, usize::MAX][rng.below(4)];
                assert!(
                    typing
                        .choices(last, rng.below(2) == 0, ToneStyle::New)
                        .len()
                        <= pushed
                );
            }
            5 => {
                let run: Vec<Option<&str>> = (0..rng.below(6))
                    .map(|_| (rng.below(4) != 0).then(|| rng.word()))
                    .collect();
                d.learn(&run);
            }
            6 => d.clear(),
            7 => {
                let garbage: Vec<u8> = (0..rng.below(64)).map(|_| rng.next() as u8).collect();
                let _ = d.reload(garbage.as_slice());
                assert!(d.begin_save().is_none(), "no file to save to");
            }
            8 => run.push(rng.word()),
            9 => run.pop(),
            10 => {
                let n = run.len();
                let first = [0, n, n.saturating_sub(1), usize::MAX][rng.below(4)];
                let old = vec![rng.word().to_string(); rng.below(3)];
                let new = vec![rng.word().to_string(); rng.below(3)];
                let _ = run.apply(&Change { first, old, new });
            }
            _ => {
                if let Some(c) = run.change(rng.below(2) == 0, Reach::LastWord, ToneStyle::New) {
                    assert_eq!(c.first + 1, run.len());
                    assert!(run.apply(&c));
                }
                if rng.below(8) == 0 {
                    run = Run::new(d.typing(), 0.99);
                }
            }
        }
    }
    cases
}
