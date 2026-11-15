//! What an input method changes in the field when a word ends: the run as it is shown, against the
//! run as it is guessed.

use crate::{ToneStyle, Typing};

/// One change to the field: syllables `first..first + old.len()` of the run read `old` and become
/// `new`, as long. The input method checks `old` against the field before it deletes anything, and
/// leaves the field alone when they differ.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Change {
    pub first: usize,
    pub old: Vec<String>,
    pub new: Vec<String>,
}

/// How far back a change may reach.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Reach {
    /// Any syllable of the run: the field reports its text, so earlier words can be checked.
    Run,
    /// Only the word that just ended, for a field that does not report its text in time.
    LastWord,
}

/// A run on its way into a field. Each syllable is shown as typed until a [`Change`] says otherwise;
/// later syllables can change earlier ones, several at once.
pub struct Run<'t> {
    typing: Typing<'t>,
    shown: Vec<String>,
    /// The interpreted and raw readings of a syllable pushed with two.
    readings: Vec<Option<(String, String)>>,
    raw_confidence: f64,
}

impl<'t> Run<'t> {
    /// A run guessed by `typing`, which should be empty. A raw reading replaces the interpreted one
    /// only as [`crate::Choices::takes_raw`] allows with `raw_confidence`.
    pub fn new(typing: Typing<'t>, raw_confidence: f64) -> Run<'t> {
        let mut run = Run {
            typing,
            shown: Vec::new(),
            readings: Vec::new(),
            raw_confidence,
        };
        while !run.typing.is_empty() {
            run.typing.pop();
        }
        run
    }

    /// A word that ended, shown as typed.
    pub fn push(&mut self, syllable: &str) {
        self.typing.push(syllable);
        self.shown.push(syllable.to_string());
        self.readings.push(None);
    }

    /// A word the input method read two ways, shown as `interpreted`.
    pub fn push_either(&mut self, interpreted: &str, raw: &str) {
        self.typing.push_either(interpreted, raw);
        self.shown.push(interpreted.to_string());
        self.readings
            .push(Some((interpreted.to_string(), raw.to_string())));
    }

    /// Removes the last syllable, as backspace into it does; the keys typed next make the syllable
    /// that replaces it.
    pub fn pop(&mut self) {
        self.typing.pop();
        self.shown.pop();
        self.readings.pop();
    }

    pub fn len(&self) -> usize {
        self.shown.len()
    }

    pub fn is_empty(&self) -> bool {
        self.shown.is_empty()
    }

    /// The run as the field shows it.
    pub fn shown(&self) -> &[String] {
        &self.shown
    }

    /// The change that brings the field to the best guess, or `None` when it already shows it.
    /// `ended` says whether the run is over, as for [`Typing::finish`].
    pub fn change(&self, ended: bool, reach: Reach, style: ToneStyle) -> Option<Change> {
        let n = self.shown.len();
        let from = match reach {
            Reach::Run => 0,
            Reach::LastWord => n.saturating_sub(1),
        };
        let wanted = self.wanted(from, ended, style);
        let differs = |i: &usize| wanted[*i - from] != self.shown[*i];
        let first = (from..n).find(differs)?;
        let last = (from..n).rev().find(differs)?;
        Some(Change {
            first,
            old: self.shown[first..=last].to_vec(),
            new: wanted[first - from..=last - from].to_vec(),
        })
    }

    /// Records that the field now shows `change`. A change taken before the run moved on (a pop, a
    /// push, another change) no longer matches what is shown: it is refused, and nothing changes.
    #[must_use = "a refused change was not recorded"]
    pub fn apply(&mut self, change: &Change) -> bool {
        let end = change.first.checked_add(change.old.len());
        let matches = end
            .and_then(|end| self.shown.get(change.first..end))
            .is_some_and(|shown| shown == change.old.as_slice());
        if !matches || change.new.len() != change.old.len() {
            return false;
        }
        let end = change.first + change.new.len();
        self.shown[change.first..end].clone_from_slice(&change.new);
        true
    }

    /// The best spelling of syllables `from..`. A syllable with two readings keeps the interpreted
    /// one unless the raw one wins with the confidence asked for.
    fn wanted(&self, from: usize, ended: bool, style: ToneStyle) -> Vec<String> {
        let n = self.shown.len();
        let guess = if ended {
            self.typing.finish(style)
        } else {
            self.typing.guess(style)
        };
        let mut wanted = guess[from..].to_vec();
        let Some(earliest) = (from..n).find(|&i| self.readings[i].is_some()) else {
            return wanted;
        };
        let choices = self.typing.choices(n - earliest, ended, style);
        for i in earliest..n {
            if let Some((interpreted, raw)) = &self.readings[i] {
                let takes = choices[i - earliest].takes_raw(raw, self.raw_confidence);
                wanted[i - from] = if takes { raw } else { interpreted }.clone();
            }
        }
        wanted
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Table;

    fn table() -> Table {
        let path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/tiny.timsen");
        Table::open(path).unwrap()
    }

    fn strings(words: &[&str]) -> Vec<String> {
        words.iter().map(|w| w.to_string()).collect()
    }

    /// Pushes each word and applies the change at each word end, as an input method would.
    fn type_words(run: &mut Run, words: &[&str], reach: Reach) {
        for w in words {
            run.push(w);
            if let Some(c) = run.change(false, reach, ToneStyle::New) {
                assert!(run.apply(&c));
            }
        }
    }

    #[test]
    fn a_later_word_changes_two_syllables_in_one_batch() {
        let t = table();
        let mut run = Run::new(Typing::new(&t), 0.99);
        type_words(&mut run, &["nguoi", "ta", "co", "go"], Reach::Run);
        assert_eq!(run.shown()[3], "gõ");
        run.push("quy");
        let change = run.change(false, Reach::Run, ToneStyle::New).unwrap();
        assert_eq!(change.first, 3);
        assert_eq!(change.old, strings(&["gõ", "quy"]));
        assert_eq!(change.new, strings(&["gỗ", "quý"]));
        assert!(run.apply(&change));
        assert_eq!(run.change(false, Reach::Run, ToneStyle::New), None);
    }

    #[test]
    fn a_field_that_does_not_report_its_text_changes_only_the_last_word() {
        let t = table();
        let mut run = Run::new(Typing::new(&t), 0.99);
        type_words(&mut run, &["nguoi", "ta", "co", "go"], Reach::LastWord);
        run.push("quy");
        let change = run.change(false, Reach::LastWord, ToneStyle::New).unwrap();
        assert_eq!(change.first, 4);
        assert_eq!(change.old, strings(&["quy"]));
        assert_eq!(change.new, strings(&["quý"]));
    }

    #[test]
    fn backspace_into_a_word_then_more_keys_replaces_it() {
        let t = table();
        let mut run = Run::new(Typing::new(&t), 0.99);
        type_words(&mut run, &["nguoi", "ta", "co", "go", "quy"], Reach::Run);
        assert_eq!(run.shown()[3], "gỗ");
        run.pop();
        run.pop();
        type_words(&mut run, &["go", "cua"], Reach::Run);
        assert_eq!(run.shown()[3], "gõ");
        assert_eq!(run.len(), 5);
    }

    #[test]
    fn a_raw_reading_needs_the_confidence_asked_for() {
        let t = table();
        for (confidence, want) in [(0.0, "file"), (1.1, "fìle")] {
            let mut run = Run::new(Typing::new(&t), confidence);
            run.push("mở");
            run.push_either("fìle", "file");
            run.push("code");
            if let Some(c) = run.change(true, Reach::Run, ToneStyle::New) {
                assert!(run.apply(&c));
            }
            assert_eq!(run.shown()[1], want, "confidence {confidence}");
        }
    }

    #[test]
    fn a_raw_reading_shown_goes_back_when_the_context_turns() {
        let t = table();
        let mut run = Run::new(Typing::new(&t), 0.0);
        run.push("mở");
        run.push_either("tét", "test");
        assert!(run.apply(&Change {
            first: 1,
            old: strings(&["tét"]),
            new: strings(&["test"]),
        }));
        let change = run.change(true, Reach::Run, ToneStyle::New).unwrap();
        assert_eq!(change.old, strings(&["test"]));
        assert_eq!(change.new, strings(&["tét"]));
    }

    #[test]
    fn a_change_that_no_longer_matches_is_refused() {
        let t = table();
        let mut run = Run::new(Typing::new(&t), 0.99);
        type_words(&mut run, &["nguoi", "ta", "co"], Reach::Run);
        run.push("go");
        let change = run.change(false, Reach::Run, ToneStyle::New).unwrap();
        run.pop();
        assert!(!run.apply(&change), "the syllable it replaces is gone");
        run.push("phim");
        assert!(!run.apply(&change), "another syllable stands there now");
        let shown = run.shown().to_vec();
        let wrong = Change {
            first: 0,
            old: shown[..1].to_vec(),
            new: strings(&["a", "b"]),
        };
        assert!(!run.apply(&wrong), "new must be as long as old");
        assert_eq!(run.shown(), shown);
    }

    #[test]
    fn an_empty_run_has_nothing_to_change() {
        let t = table();
        let run = Run::new(Typing::new(&t), 0.99);
        assert!(run.is_empty());
        assert_eq!(run.change(true, Reach::LastWord, ToneStyle::New), None);
    }
}
