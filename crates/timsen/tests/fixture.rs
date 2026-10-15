//! Compares the crate with `research.model` on the table in `fixtures/`, built by `research.fixture`.

use std::path::Path;

use timsen::{Table, ToneStyle};

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
