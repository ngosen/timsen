//! Compares the crate with `research.model` on the table in `fixtures/`, built by `research.fixture`.

use std::path::Path;

use timsen::{Personal, Table, ToneStyle};

fn fixture(name: &str) -> std::path::PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures")
        .join(name)
}

fn table() -> Table {
    Table::open(fixture("tiny.timsen")).unwrap()
}

#[test]
fn restores_exactly_like_the_python_model() {
    let t = table();
    let runs = std::fs::read_to_string(fixture("tiny.runs")).unwrap();
    let expected = std::fs::read_to_string(fixture("tiny.expected")).unwrap();
    assert_eq!(runs.lines().count(), expected.lines().count());
    for (run, want) in runs.lines().zip(expected.lines()) {
        let words: Vec<&str> = run.split(' ').collect();
        assert_eq!(
            t.restore(&words, ToneStyle::New).join(" "),
            want,
            "run: {run}"
        );
    }
}

#[test]
fn keeps_capitalization_and_unknown_words() {
    let got = table().restore(&["Toi", "go", "PHIM", "Commit"], ToneStyle::New);
    assert_eq!(got, ["Tôi", "gõ", "PHÍM", "Commit"]);
}

#[test]
fn old_tone_placement_on_request() {
    let t = table();
    assert_eq!(t.restore(&["hoa", "binh"], ToneStyle::New), ["hoà", "bình"]);
    assert_eq!(t.restore(&["hoa", "binh"], ToneStyle::Old), ["hòa", "bình"]);
    assert_eq!(t.restore(&["Thuy", "loi"], ToneStyle::Old), ["Thủy", "lợi"]);
}

#[test]
fn empty_run_restores_to_nothing() {
    assert!(table().restore(&[], ToneStyle::New).is_empty());
}

#[test]
fn rejects_files_that_are_not_tables() {
    assert!(Table::from_bytes(b"not a table".to_vec()).is_err());
    let mut bytes = std::fs::read(fixture("tiny.timsen")).unwrap();
    bytes.truncate(bytes.len() - 100);
    assert!(Table::from_bytes(bytes).is_err());
}

/// A table file of its own, removed when dropped.
struct TempTable(std::path::PathBuf);

impl TempTable {
    fn new(name: &str, bytes: &[u8]) -> TempTable {
        let path = std::env::temp_dir().join(format!("timsen-{}-{name}", std::process::id()));
        std::fs::write(&path, bytes).unwrap();
        TempTable(path)
    }
}

impl Drop for TempTable {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

#[test]
fn an_open_table_ignores_its_file_being_rewritten_in_place() {
    use std::io::Write;
    let bytes = std::fs::read(fixture("tiny.timsen")).unwrap();
    let file = TempTable::new("rewritten", &bytes);
    let t = Table::open(&file.0).unwrap();
    let before = t.restore(&["toi", "go", "phim"], ToneStyle::New);
    // An update that writes over the file instead of replacing it, as `cp` onto an existing file does.
    let mut f = std::fs::OpenOptions::new()
        .write(true)
        .open(&file.0)
        .unwrap();
    f.write_all(&vec![0xff; bytes.len()]).unwrap();
    f.sync_all().unwrap();
    assert_eq!(t.restore(&["toi", "go", "phim"], ToneStyle::New), before);
}

#[test]
fn opening_a_broken_file_is_an_error() {
    let mut bytes = std::fs::read(fixture("tiny.timsen")).unwrap();
    bytes.truncate(bytes.len() - 100);
    let file = TempTable::new("truncated", &bytes);
    assert!(Table::open(&file.0).is_err());
    assert!(Table::open(std::env::temp_dir().join("timsen-no-such-table")).is_err());
}

#[test]
fn restores_with_learned_counts_exactly_like_the_python_model() {
    let t = table();
    let mut personal = Personal::new(&t);
    for run in std::fs::read_to_string(fixture("tiny.learned"))
        .unwrap()
        .lines()
    {
        let words: Vec<Option<&str>> = run.split(' ').map(Some).collect();
        personal.learn(&words);
    }
    let runs = std::fs::read_to_string(fixture("tiny.runs")).unwrap();
    let expected = std::fs::read_to_string(fixture("tiny.personal.expected")).unwrap();
    let before = std::fs::read_to_string(fixture("tiny.expected")).unwrap();
    assert_ne!(expected, before, "the learned text should change some runs");
    assert_eq!(runs.lines().count(), expected.lines().count());
    for (run, want) in runs.lines().zip(expected.lines()) {
        let words: Vec<&str> = run.split(' ').collect();
        let got = personal.restore(&words, ToneStyle::New).join(" ");
        assert_eq!(got, want, "run: {run}");
    }
}
