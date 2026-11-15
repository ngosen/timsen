//! The user's one personal dictionary, kept by the input method and read by every field through
//! snapshots.

use std::io::{BufRead, Write};
use std::sync::Arc;

use crate::{Error, Personal, Table, Typing};

/// Owns the personal dictionary for one user. Each run reads the snapshot taken when it started:
/// learning, a clear or a reload makes a new snapshot that only later runs see, so a run never mixes
/// two sets of counts and the ids it holds stay valid until it ends.
pub struct Dictionary {
    table: Arc<Table>,
    current: Arc<Personal<'static>>,
}

impl Dictionary {
    /// An empty dictionary for this table.
    pub fn new(table: Arc<Table>) -> Dictionary {
        let current = Arc::new(Personal::shared(Arc::clone(&table)));
        Dictionary { table, current }
    }

    /// A dictionary read from a file written by [`Dictionary::save`] or [`Personal::save`].
    pub fn load(table: Arc<Table>, input: impl BufRead) -> Result<Dictionary, Error> {
        let current = Arc::new(Personal::load_shared(Arc::clone(&table), input)?);
        Ok(Dictionary { table, current })
    }

    pub fn table(&self) -> &Arc<Table> {
        &self.table
    }

    /// The counts as they are now; later changes do not reach it.
    pub fn snapshot(&self) -> Arc<Personal<'static>> {
        Arc::clone(&self.current)
    }

    /// A new run on the current snapshot.
    pub fn typing(&self) -> Typing<'static> {
        Typing::with_shared_personal(self.snapshot())
    }

    pub fn is_empty(&self) -> bool {
        self.current.is_empty()
    }

    /// Learns a run as [`Personal::learn`] does. The counts are copied first only while a run still
    /// holds the current snapshot.
    pub fn learn(&mut self, run: &[Option<&str>]) {
        Arc::make_mut(&mut self.current).learn(run);
    }

    /// Forgets everything learned; runs already started keep what they had.
    pub fn clear(&mut self) {
        self.current = Arc::new(Personal::shared(Arc::clone(&self.table)));
    }

    /// Replaces the counts with a file's. A file that does not load leaves the dictionary as it was.
    pub fn reload(&mut self, input: impl BufRead) -> Result<(), Error> {
        let loaded = Personal::load_shared(Arc::clone(&self.table), input)?;
        self.current = Arc::new(loaded);
        Ok(())
    }

    pub fn save(&self, out: &mut impl Write) -> std::io::Result<()> {
        self.current.save(out)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ToneStyle;

    fn dictionary() -> Dictionary {
        let path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/fixtures/tiny.timsen");
        Dictionary::new(Arc::new(Table::open(path).unwrap()))
    }

    fn guess(typing: &mut Typing, run: &[&str]) -> Vec<String> {
        for syllable in run {
            typing.push(syllable);
        }
        typing.finish(ToneStyle::New)
    }

    #[test]
    fn a_run_keeps_its_snapshot_and_the_next_run_sees_the_learning() {
        let mut d = dictionary();
        let mut before = d.typing();
        before.push("ngo");
        d.learn(&[Some("ngó"), Some("sen")]);
        before.push("sen");
        assert_eq!(before.finish(ToneStyle::New), ["ngo", "sen"]);
        assert_eq!(guess(&mut d.typing(), &["ngo", "sen"]), ["ngó", "sen"]);
    }

    #[test]
    fn learning_while_no_run_holds_the_snapshot_does_not_copy_it() {
        let mut d = dictionary();
        d.learn(&[Some("ngó"), Some("sen")]);
        let at = Arc::as_ptr(&d.current);
        d.learn(&[Some("gỗ")]);
        assert_eq!(Arc::as_ptr(&d.current), at);
        let held = d.snapshot();
        d.learn(&[Some("gõ")]);
        assert_ne!(Arc::as_ptr(&d.current), Arc::as_ptr(&held));
    }

    #[test]
    fn a_clear_reaches_only_later_runs() {
        let mut d = dictionary();
        d.learn(&[Some("ngó"), Some("sen")]);
        let mut before = d.typing();
        d.clear();
        assert!(d.is_empty());
        assert_eq!(guess(&mut before, &["ngo", "sen"]), ["ngó", "sen"]);
        assert_eq!(guess(&mut d.typing(), &["ngo", "sen"]), ["ngo", "sen"]);
    }

    #[test]
    fn a_file_that_does_not_load_leaves_the_dictionary_as_it_was() {
        let mut d = dictionary();
        d.learn(&[Some("ngó"), Some("sen")]);
        let at = Arc::as_ptr(&d.current);
        assert!(d.reload("not a dictionary\n".as_bytes()).is_err());
        assert_eq!(Arc::as_ptr(&d.current), at);
        assert_eq!(guess(&mut d.typing(), &["ngo", "sen"]), ["ngó", "sen"]);
    }

    #[test]
    fn a_reload_replaces_the_counts_for_later_runs() {
        let mut d = dictionary();
        let mut file = Vec::new();
        d.learn(&[Some("ngó"), Some("sen")]);
        d.save(&mut file).unwrap();
        d.clear();
        let mut before = d.typing();
        d.reload(file.as_slice()).unwrap();
        assert_eq!(guess(&mut before, &["ngo", "sen"]), ["ngo", "sen"]);
        assert_eq!(guess(&mut d.typing(), &["ngo", "sen"]), ["ngó", "sen"]);
    }
}
