# Changelog

All notable changes to Tim Sen. The format follows [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Changed

- Table format version 3: a count is one byte (one of 256 levels) and a bigram's trigrams are found
  from a length byte, so the same n-grams take about half the file: the small table goes from
  22.65 MB to 12.37 MB with the same accuracy. The crate reads version 3 only; a version 2 file is
  an `Error`. Opening no longer passes over every n-gram, and the table takes no memory beyond its
  file.
- The large table is now 49.69 MB instead of 130.96 MB, and scores 97.04% on Wikipedia, 96.55% on
  subtitles and 94.26% on forum text (the 130.96 MB one: 97.15%, 96.59%, 94.30%). On chat with
  the personal dictionary the small table stays ahead (89.24% and 88.49%), so it stays the default.

### Fixed

- `research.prune --bytes` kept every n-gram when the budget had room for none, and could write a
  file over the budget when many n-grams weighed the same as the last one kept.
- A table written from the same model is now the same file on every machine: the floats it stores
  are rounded to single precision, since `exp` and `log` differ in the last bit between CPUs.

### Added

- `research.quant`: scores a table with its counts rounded to a few bits; one byte per count loses
  nothing measurable.
- `research.external`: scores another program's restoration of a test file on the words
  `research.evaluate` counts; used to measure VietTelex's 2 MB model on the frozen test files.
- `Typing::shared`, `Typing::with_shared_personal`, `Personal::shared` and `Personal::load_shared`
  take the table or dictionary as an `Arc`, so an input method can keep a run in each field with no
  lifetime. The borrowing constructors are unchanged.
- `Dictionary` keeps one personal dictionary for every field. `Dictionary::typing` starts a run on
  the snapshot taken then; `learn`, `clear` and `reload` make a new snapshot that only later runs
  see, so a run never mixes two sets of counts. A file that fails to reload leaves it as it was.
- `Dictionary::open` keeps the dictionary in a file it never loses. A file that does not load is
  left byte for byte and saving stops until `start_empty`, which renames it to `<name>.broken`.
  `begin_save`, `SaveJob::write`, `finish_save`, `SyncJob::sync` and `finish_sync` replace the
  file whole (readable by the user only, synced, renamed into place), one save at a time, and drop
  a save begun before a clear or reload. Writing and syncing need no access to the dictionary, so
  an input method does both with its lock released. `reload_file` keeps what was learned since the last save. Lines naming a word the table
  cannot take are written back unchanged.
- `Run` tracks a run as the field shows it and, when a word ends, gives one `Change`: the syllables
  it replaces as the field shows them and their new spellings, so the input method checks the old
  text before it deletes. `Reach::LastWord` keeps the change to the word that just ended, for fields
  that do not report their text; `pop` handles backspace into a word. A raw reading replaces the
  interpreted one only with the confidence the run was given. `Run::apply` refuses a change the run
  has moved past instead of panicking.
- `MAX_RUN` (200 syllables), `Run::is_full` and `Run::next`: at the cap the input method ends the
  run and goes on in a new one, on a typing it takes from the dictionary again, that reads the last
  two syllables as context only, neither shown again nor learned twice. A key at word end stays
  under 2.5 ms at p99 at 50 and 200 syllables on both tables with a 193,000-word personal
  dictionary (Xeon E5-2696 v4, busy machine), and near 3 ms with one word in 20 read two ways.
- `Typing::fix` finds the known syllable one edit away that scores best in context for a syllable
  the table does not know (`khogn` → `không`), with its margin over the runner-up and over keeping
  it, exactly as `research.typo` decides. `Run::fixing(Some(FIX_MARGIN))` makes a run fix a word
  when it ends, from the words before it, if the fix wins by the margin; fixing is off by default.
  `Run::undo_fix` takes the latest fix back and keeps the syllable as typed, also after the run
  ended; `Run::last_fix` says where that fix is, so a key can undo only the fix just made, and
  `Run::push_as_typed` takes a word that must stay as typed, such as one reopened by an undo and
  committed again; `Run::apply` refuses a change taken earlier that would alter such a word.
  Only words of plain letters in lowercase, capitals or with a capital first are fixed, and keep
  that case; a word the personal dictionary knows is never fixed, so learning an undone fix as
  typed keeps it as typed.
- `Typing::fix_nearby` and `Run::push_nearby` fix a syllable nothing knows to one of the words an
  input method found near the keys typed (`mguoifw` → `người`), which one plain-letter edit does
  not reach once Telex marks were typed. Each `Nearby` word has a cost, 1 for a slip made easily,
  and loses 2 points of score per unit; the fix is the word's best spelling and must win by the
  same margin, exactly as `research.telex_typo` decides. `Run::may_fix` says whether a syllable
  could be fixed, so the input method looks for nearby words only then. With Ngó Sen's core
  finding the words one slip away, at `FIX_MARGIN` it puts right 12.6% to 17.1% of mistyped Telex
  words (`Typing::fix` alone: 4.3% to 6.0%), is right 99.5% to 99.9% of the time and changes at
  most 0.006% of the words typed right. `Fix::word` is the form to show for either fix.
- `Run::fixing_again` decides a syllable `Run::push_nearby` left as typed once more when the word
  after it ends, with that word as context too, as `research.telex_typo --then` does. The fix then
  changes the word before the last, so it is for a field whose earlier words can change
  (`Reach::Run`). At `FIX_MARGIN` on unseen Wikipedia and forum text it puts right 30.6% and 30.1%
  of mistyped Telex words (17.1% and 14.4% without it) and is right 99.8% and 99.6% of the time.
  The setting counts when the word after ends, not when the syllable does, so it can be turned on
  for a field that shows its text only from its second word.
- `scripts/abuse.sh` builds an abuse binary with Ngó Sen's release profile (`panic = "abort"`) and
  again with overflow checks, and feeds it truncated and corrupt tables and personal files, odd text
  and calls in any order; CI runs it. A table cut short is an error unless the cut took only the
  padding after the last section, and then it restores exactly like the whole one.

### Changed

- A word pushed with `Run::push_either` is weighed on each key only while it is among the last four
  syllables, then keeps the reading decided when it leaves them, so its cost no longer grows with
  the run. It ends as weighing the whole run would in 99.9% of cases.
- Errors read "cannot read file" and "not a valid file", since they come from personal files too.
- The crate declares Rust 1.88 as its minimum, Ngó Sen's, and CI builds and tests on it.
- `Table::open` reads the whole table into memory instead of mapping it, so a table file written
  over during an update no longer changes, or crashes, a running program. The crate no longer
  depends on `memmap2`. Opening the small table takes about 12 ms more; memory once typing has
  touched it is the same (31 MB).
- `Choices::takes_raw` decides whether a raw reading replaces the interpreted one, and asks
  `SENSITIVE_CONFIDENCE` (0.9999) for crude words (`sex`, `ass`, `piss`, `tits`): on mixed text
  at 0.99 it removes the one `sẽ` → `sex` and fixes the same English words.
- `Personal` in the crate, `research.crosscheck` and `research.personal auto` weigh a learned n-gram
  min(3000, table total / tokens learned) times one from the corpora instead of a fixed 1000, so a
  dictionary of years of text no longer drowns the table: on the user's messages +0.35 to +0.48 points
  with up to a year learned, the same as the best fixed weight with more; +0.22 on chat. `WEIGHT` is
  replaced by `MAX_WEIGHT` and `Personal::weight`.
- The tables are trained with a technology-forum slice of FineWeb-2 (`research.fetch_fineweb
  tech`, 30 million words from tinhte.vn, voz.vn, viblo.asia and others): +0.31 points on chat with
  the personal dictionary for the small table, +0.53 for the large one, edited prose within 0.08.
  The forum corpus leaves those hosts out, so no page is counted twice; forum pages from FineWeb-2
  files 5 to 29 are not used, since they cost up to 0.95 points on wiki and nothing on chat.
- `research.personal --learn FILE`: learns the personal dictionary from one file and scores another,
  for a split by time instead of 5 folds.
- `research.prune --min-candidate N`: how often a spelling must be seen to be offered, for corpora
  large enough to bring more rare spellings than a table has word ids.
- Table format version 2: n-grams grouped by their first words, 6 bytes each plus 4 per bigram
  instead of 12, counts unchanged. Version 1 files are no longer read. The small table holds 65% more
  n-grams in the same 22.65 MB (+0.43 points on wiki, +0.57 on forum), and restore is faster (p99
  per syllable 0.63 ms against 1.50).
- `research.prune --bytes N`: keeps as many n-grams as fit in a file of that size.
- Restore, in `research.model` and the crate, charges more for backing off from a context whose
  continuations the table kept nearly whole: +0.21 on wiki and +0.27 on forum with the small
  weighted table. Opening a table takes one pass over its n-grams (about 50 ms for the small one).
- `Personal` in the crate and `research.crosscheck` weigh a learned n-gram 1000 times one from the
  corpora, up from 100: 0.66 to 0.71 points more on chat.
- `Personal` scores learned words the table lacks as the table's `<unk>`, so a personal dictionary
  learned from text with English or code words guesses the Vietnamese around them as well as
  `research.personal` does (#20).
- `research.personal` adds learned counts to a table file's total instead of recomputing it from the
  words the file keeps (#18).
- `docs/DATA_SOURCES.md`: OpenSubtitles counts may ship in released tables, with a link to
  opensubtitles.org and the OPUS citation (#17).
- `docs/PLAN.md`, `docs/TABLES.md`: the small table ships first; stupid backoff stays after measuring
  Kneser-Ney at the shipped sizes (#11).
- `docs/PLAN.md`: two shipped tables, 44 MB and 177 MB, chosen by the user (#9).
- `docs/PLAN.md`: mixed marked/unmarked input, both readings of a word, abbreviations kept as typed,
  new words in the personal dictionary, and what is taken from users (#5).

### Added

- `research.train --breaks` and `research.evaluate --breaks`: runs that go on across commas, digits
  and symbols, which become one `<p>` word. Not used for the shipped tables (+0.01 to +0.13 points at
  the small size).
- `research.prune`: builds a table that keeps the n-grams whose removal would change scores most, at a
  given number of n-grams: +0.59 points on wiki at the small table's size, +0.32 at the large one's.
- `research.coverage`: the share of words whose right spelling is among restore's candidates.
- `research.evaluate --backoff X` and `research.personal --backoff X`.
- `Personal` in the `timsen` crate: a personal dictionary that learns runs known to be right,
  including words the table lacks, and saves them as a text file; `Typing::with_personal` and
  `Personal::restore` use it (#18).
- `Typing::push` keeps a word typed with marks as typed, in either tone placement, and uses it as
  context; `Typing::push_either` chooses between an input method's reading of a word and its raw
  letters (#16).
- `Typing::choices`: up to three spellings for each of the last few words, best first, with a
  confidence for the first (#15).
- `Typing` in the `timsen` crate: the best spelling of a run after each syllable, with `pop` for
  backspace; `Table::restore` now goes through it (#14).
- `timsen` crate: maps a `.timsen` table and restores a run of unmarked syllables, keeping
  capitalization, in new or old tone placement; same output as `research.model` (#12).
- `research.crosscheck` and `research.fixture`: compare another implementation with the Python model
  run by run (#12).
- `research.table --min-plain N`: leaves rare words that restore as typed out of the table, which
  shrinks the small table from 44 MB to 22.6 MB; `research.personal` reads `.timsen` files (#11).
- `docs/TABLES.md`: accuracy of every measured table size, to help users choose between the two
  shipped tables (#10).
- `research.table`: writes a pruned model as a fixed binary table (`.timsen`) that can be mapped from
  disk without parsing; `research.evaluate` scores such a table directly (#8).
- `research.personal --min-tri/--min-bi`: the personal dictionary on top of a pruned table (#8).
- `docs/PLAN.md`: steps from the research code to a Rust library (#4).
- `research.train --order 4`: stupid-backoff 4-grams, kept for comparison with Kneser-Ney (#3).
- `research.kn_export` and `research.kn_model`: Kneser-Ney models estimated with KenLM, read from
  ARPA and scored with beam search (#2).
- `research.typing_sim`: accuracy when words are fixed as typed, and how often the model could ask
  instead of guessing (#1).
- Research code to train a syllable trigram model from Wikipedia, OpenSubtitles and FineWeb-2 and to
  measure diacritic restoration, context spell checking and a personal dictionary.

### Fixed

- `Personal`: a saved file reloads as it was saved. Words with spaces, tabs or control characters
  and the run markers `<s>`, `</s>` are no longer learned, since they broke the file; equal-scoring
  new spellings keep their order; counts saturate instead of overflowing, and `load` rejects counts
  above 2^40. One unmarked form keeps at most 256 spellings (#22).
- `Table::open` and `Table::from_bytes` return an `Error` for damaged files that could panic: section
  sizes that overflow, unmarked forms with no, repeated or too many spellings. `Table::word` is no
  longer public, since a wrong id panicked (#21).
