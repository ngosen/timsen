//! The word-end contract for any keys: a change says exactly what the field shows in the part it
//! replaces, keeps every syllable's letters and capitalization, and leaves the rest alone.

use proptest::prelude::*;
use proptest::strategy::ValueTree;
use timsen::{Change, Reach, Run, Table, ToneStyle, Typing};

fn table() -> Table {
    Table::open(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/tests/fixtures/tiny.timsen"
    ))
    .unwrap()
}

#[derive(Clone, Debug)]
enum Op {
    Push(String),
    Either(String, String),
    Pop,
    End(Reach, bool),
}

fn cased(word: String, how: u8) -> String {
    match how {
        0 => word.to_uppercase(),
        1 => {
            let mut c = word.chars();
            c.next()
                .map(|f| f.to_uppercase().chain(c).collect())
                .unwrap_or_default()
        }
        _ => word,
    }
}

fn syllable() -> impl Strategy<Value = String> {
    let words = vec![
        "nguoi", "ta", "co", "go", "quy", "cua", "nha", "phim", "toi", "da", "ban", "thich",
    ];
    let plain = prop_oneof![
        4 => prop::sample::select(words).prop_map(str::to_string),
        1 => "[a-z]{1,4}",
        1 => Just("gõ".to_string()),
    ];
    (plain, 0..6u8).prop_map(|(w, how)| cased(w, how))
}

fn op() -> impl Strategy<Value = Op> {
    let either = prop::sample::select(vec![("tét", "test"), ("fìle", "file"), ("sẽ", "sex")]);
    let reach = prop_oneof![Just(Reach::Run), Just(Reach::LastWord)];
    prop_oneof![
        6 => syllable().prop_map(Op::Push),
        1 => either.prop_map(|(a, b)| Op::Either(a.to_string(), b.to_string())),
        1 => Just(Op::Pop),
        4 => (reach, any::<bool>()).prop_map(|(r, e)| Op::End(r, e)),
    ]
}

/// Uppercase flags letter by letter, and the letter count: what a restored word must keep.
fn shape(word: &str) -> Vec<bool> {
    word.chars().map(char::is_uppercase).collect()
}

fn check(field: &[String], typed: &[Op], c: &Change, reach: Reach) -> Result<(), TestCaseError> {
    let n = field.len();
    prop_assert!(!c.old.is_empty());
    prop_assert_eq!(c.old.len(), c.new.len());
    prop_assert!(c.first + c.old.len() <= n);
    prop_assert_eq!(&field[c.first..c.first + c.old.len()], c.old.as_slice());
    prop_assert!(c.old.first() != c.new.first() && c.old.last() != c.new.last());
    if reach == Reach::LastWord {
        prop_assert_eq!(c.first, n - 1);
    }
    for (i, new) in (c.first..).zip(&c.new) {
        match &typed[i] {
            Op::Push(t) => prop_assert_eq!(shape(new), shape(t), "{} for {}", new, t),
            Op::Either(a, b) => prop_assert!(new == a || new == b),
            _ => unreachable!("only pushes stay in the run"),
        }
    }
    Ok(())
}

proptest! {
    #[test]
    fn a_change_replaces_exactly_what_it_reports(ops in prop::collection::vec(op(), 1..40)) {
        let t = table();
        let mut run = Run::new(Typing::new(&t), 0.99);
        let mut field: Vec<String> = Vec::new();
        let mut typed: Vec<Op> = Vec::new();
        for op in &ops {
            match op {
                Op::Push(s) => {
                    run.push(s);
                    field.push(s.clone());
                    typed.push(op.clone());
                }
                Op::Either(a, b) => {
                    run.push_either(a, b);
                    field.push(a.clone());
                    typed.push(op.clone());
                }
                Op::Pop => {
                    run.pop();
                    field.pop();
                    typed.pop();
                }
                Op::End(reach, ended) => {
                    if let Some(c) = run.change(*ended, *reach, ToneStyle::New) {
                        check(&field, &typed, &c, *reach)?;
                        let before = field.clone();
                        field[c.first..c.first + c.new.len()].clone_from_slice(&c.new);
                        run.apply(&c);
                        // Outside the change, nothing moved.
                        prop_assert_eq!(&field[..c.first], &before[..c.first]);
                        let end = c.first + c.new.len();
                        prop_assert_eq!(&field[end..], &before[end..]);
                        prop_assert_eq!(run.change(*ended, *reach, ToneStyle::New), None);
                    }
                }
            }
            prop_assert_eq!(run.shown(), field.as_slice());
            prop_assert_eq!(run.len(), typed.len());
        }
    }

    #[test]
    fn a_whole_run_ends_as_the_table_restores_it(words in prop::collection::vec(syllable(), 1..12)) {
        let t = table();
        let mut run = Run::new(Typing::new(&t), 0.99);
        for w in &words {
            run.push(w);
            if let Some(c) = run.change(false, Reach::Run, ToneStyle::New) {
                run.apply(&c);
            }
        }
        if let Some(c) = run.change(true, Reach::Run, ToneStyle::New) {
            run.apply(&c);
        }
        let words: Vec<&str> = words.iter().map(String::as_str).collect();
        prop_assert_eq!(run.shown().to_vec(), t.restore(&words, ToneStyle::New));
    }
}

#[test]
fn several_syllables_change_at_once_somewhere() {
    // The property above must meet a change of more than one syllable, or it proves little about
    // batches: count them over the same kind of runs.
    let t = table();
    let mut runner = proptest::test_runner::TestRunner::deterministic();
    let mut wide = 0;
    for _ in 0..200 {
        let words = prop::collection::vec(syllable(), 2..10)
            .new_tree(&mut runner)
            .unwrap()
            .current();
        let mut run = Run::new(Typing::new(&t), 0.99);
        for w in &words {
            run.push(w);
            if let Some(c) = run.change(false, Reach::Run, ToneStyle::New) {
                wide += usize::from(c.new.len() > 1);
                run.apply(&c);
            }
        }
    }
    assert!(wide > 0, "no change covered two syllables");
}
