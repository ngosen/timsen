//! A damaged table file must give an `Error` when opened, or else restore without panicking.

use proptest::prelude::*;
use timsen::{Table, ToneStyle, Typing};

fn fixture() -> Vec<u8> {
    std::fs::read(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/tests/fixtures/tiny.timsen"
    ))
    .unwrap()
}

fn u64_at(b: &[u8], pos: usize) -> usize {
    u64::from_le_bytes(b[pos..pos + 8].try_into().unwrap()) as usize
}

fn u32_at(b: &[u8], pos: usize) -> usize {
    u32::from_le_bytes(b[pos..pos + 4].try_into().unwrap()) as usize
}

fn put_u32(b: &mut [u8], pos: usize, v: u32) {
    b[pos..pos + 4].copy_from_slice(&v.to_le_bytes());
}

/// Where the candidate ranges and ids start, following the layout in `research/table.py`.
fn candidates(b: &[u8]) -> (usize, usize, usize) {
    let pad = |x: usize| x.next_multiple_of(8);
    let (n_words, n_bi, n_tri, n_plain) =
        (u64_at(b, 16), u64_at(b, 24), u64_at(b, 32), u64_at(b, 40));
    let strings = |pos: usize, n: usize| pad(pad(pos + 4 * (n + 1)) + u32_at(b, pos + 4 * n));
    let mut pos = strings(64, n_words);
    pos = pad(pos + 4 * n_words);
    pos = pad(pad(pos + 8 * n_bi) + 4 * n_bi);
    pos = pad(pad(pos + 8 * n_tri) + 4 * n_tri);
    pos = strings(pos, n_plain);
    (pos, pad(pos + 4 * (n_plain + 1)), n_plain)
}

/// Restores and types a few runs, touching every lookup.
fn exercise(t: &Table) {
    let _ = t.restore(&["toi", "go", "phim", "rat", "nhanh"], ToneStyle::New);
    let mut typing = Typing::new(t);
    for s in ["nha", "ta", "co", "go", "quy", "xyz"] {
        typing.push(s);
        let _ = typing.guess(ToneStyle::Old);
        let _ = typing.choices(3, false, ToneStyle::New);
    }
}

#[test]
fn the_fixture_layout_is_understood() {
    let b = fixture();
    let (start, ids, n_plain) = candidates(&b);
    assert_eq!(u32_at(&b, start), 0);
    assert_eq!(u32_at(&b, start + 4 * n_plain), u64_at(&b, 48));
    assert_eq!((ids + 4 * u64_at(&b, 48)).next_multiple_of(8), b.len());
}

#[test]
fn huge_section_counts_are_errors() {
    for field in [16, 24, 32, 40, 48] {
        for n in [u64::MAX, u64::MAX / 4, 1 << 62, 1 << 61, (1 << 62) + 1] {
            let mut b = fixture();
            b[field..field + 8].copy_from_slice(&n.to_le_bytes());
            assert!(Table::from_bytes(b).is_err(), "field {field} = {n}");
        }
    }
}

#[test]
fn a_form_without_spellings_is_an_error() {
    let mut b = fixture();
    let (start, _, _) = candidates(&b);
    let third = u32_at(&b, start + 8);
    put_u32(&mut b, start + 4, 0);
    assert!(Table::from_bytes(b.clone()).is_err());
    // A range that runs backwards is as bad.
    put_u32(&mut b, start + 4, third as u32 + 1);
    assert!(Table::from_bytes(b).is_err());
}

#[test]
fn a_repeated_spelling_is_an_error() {
    let mut b = fixture();
    let (start, ids, n_plain) = candidates(&b);
    let form = (0..n_plain)
        .find(|&i| u32_at(&b, start + 4 * (i + 1)) - u32_at(&b, start + 4 * i) >= 2)
        .unwrap();
    let first = u32_at(&b, start + 4 * form);
    let id = u32_at(&b, ids + 4 * first) as u32;
    put_u32(&mut b, ids + 4 * (first + 1), id);
    assert!(Table::from_bytes(b).is_err());
}

proptest! {
    #[test]
    fn damaged_bytes_never_panic(flips in prop::collection::vec((any::<prop::sample::Index>(), any::<u8>()), 1..8)) {
        let mut b = fixture();
        for (at, byte) in flips {
            let i = at.index(b.len());
            b[i] = byte;
        }
        if let Ok(t) = Table::from_bytes(b) {
            exercise(&t);
        }
    }
}
