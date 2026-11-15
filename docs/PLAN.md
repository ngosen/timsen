# Plan

From research code to a library input methods can use. Each step is one or more pull requests with
tests, and each measurement goes into [`EXPERIMENTS.md`](EXPERIMENTS.md) with its prediction.

## First release

What a Ngó Sen user on Linux gets:

- **Marks while typing, in every application.** Type without marks, or in Telex as usual, or mixed;
  the last few words are restored as you type and may still change. Tab changes a guess, Esc keeps
  what was typed.
- **A personal dictionary** that learns from words typed with marks and from corrected guesses, on
  the user's machine only.
- **Fixing syllables that do not exist** (`khogn` → `không`), only when sure, off by default.

Standard Vietnamese only: chat is covered when it is written in full words, abbreviations (`ko`,
`dc`) stay as typed, and informal spellings (`lun`, `dị` for `vậy`, `gòi`) wait (see Later). Not in
the first release: next-word suggestions, the spell check underline, macOS and Windows.

Why this shape ([`PRIOR_WORK.md`](PRIOR_WORK.md)): input methods keep n-grams at their core, and an
automatic correction pays only when it is rarely wrong and cheap to undo. Adding marks while typing
already exists in the Cốc Cốc browser (its own text fields only, sent to its servers until 2018) and
in TocKyVNKey on Windows, but no open-source input method on Linux does it. Nothing typed leaves the
machine; the only thing a user may choose to send is a score (see "From users").

## Decisions

- **Model:** syllable 3-grams with stupid backoff, in two tables of the same format, built by
  `research.prune --bytes`: small (22.65 MB), **the default**, and large (130.96 MB). Both leave out
  unmarked words seen fewer than 1,000 times whose only spelling is themselves. With the personal
  dictionary the small one is ahead on chat (92.58% and 92.21%); on edited prose the large one leads
  by about one point (wiki 96.08% and 97.21%), `docs/TABLES.md`. The small table ships first; the
  large one is added later if users ask for better accuracy on longer writing. Kneser-Ney at the
  same sizes gained 0.3–0.5 points on edited prose and 0–0.3 on chat over the count-pruned tables,
  but cannot take personal counts by simple addition; revisit only with a measured way to combine it
  with the personal dictionary. No neural restore model was trained; an off-the-shelf XLM-R marker
  scored 86.9% on wiki.
- **Corpora:** Wikipedia, OpenSubtitles and FineWeb-2 forum pages. OpenSubtitles has no formal
  licence; the tables ship its counts with attribution, as `wordfreq` does, and are rebuilt without
  it if a takedown request comes (`docs/DATA_SOURCES.md`).
- **Where the gain is:** the personal dictionary (+3.2 to +3.6 points on chat depending on the
  table: 88.63% → 92.19% small, 89.25% → 92.42% large, "Personal dictionary in Rust", after the
  total fix; it was still rising with more learned text before that fix, not rerun since) and revising the last few words
  while typing (89% against 80% when each word is fixed as typed). More general text gives about
  half a point per doubling. After that, the gain is in how cheap a wrong guess is to fix: at 92%,
  one word in twelve.
- **More general text comes from more forum files, not from users.** Counts donated by users would be
  a small forum with a privacy cost; the personal dictionary gains because the text is the user's own.
  The only thing taken from users is a score measured on their machine (see "From users").
- **Abbreviations stay as typed.** `ko`, `e`, `ok`, `j`, `b` are already kept right, since the forum
  text uses them. `a` is marked wrongly 22% of the time, but forcing it would break `ạ` and `à` about
  as often. Expanding them (`ko` → `không`) is the input method's macro table, opt-in.

## Steps

1. **Shipped table.** Done: `research.table` writes the fixed binary format (`research.prune`
   chooses the n-grams to keep), and both tables are
   measured alone on chat, wiki and forum, and on chat with the personal dictionary
   (`docs/EXPERIMENTS.md`, "Pruned table for shipping" and "Trimming the table vocabulary").
2. **Whole-run restore in Rust.** Done: the `timsen` crate (`crates/timsen`) reads a table and
   restores a run, keeping the user's capitalization and following the tone placement setting. It
   restores every run of the wiki, subs, web and forum sets exactly like `research.model` on both
   tables (`docs/EXPERIMENTS.md`, "Rust restore against the Python model"); CI checks it on a small
   fixture table.
3. **Restore while typing.** Done.
   - `Typing` in the crate gives the best spelling after each syllable in under 2 ms at p99; words
     three syllables back are as good as final ("Restoring while typing").
   - `Typing::choices` gives the top three spellings and a confidence per word. At 0.9, a newly
     shown word marked sure is right 97–98% of the time, and over 90% of the words that later change
     were below 0.9 when shown ("Confidence and choices while typing").
   - A syllable typed with marks is kept as typed and serves as context for the guessed ones
     (0.7–1.4 points better next to them). `push_either` takes both readings of a word, as
     interpreted (`tét`) and as raw letters (`test`); the library knows nothing about Telex or VNI.
     Typed in Telex through bamboo-core alone, switching to the raw reading at confidence 0.99
     fixes 21–153 words per test set and breaks none; below that the raw reading is only a
     suggestion ("Marked words and two readings"). Through Ngó Sen's own core on mixed English and
     Vietnamese it breaks 1 and 4 words ("Near certainty before switching to a crude word").
4. **Personal dictionary.** Done. Learns syllable 2- and 3-gram counts only from text known to be
   right: words the user typed with marks, and guesses the user corrected, so a wrong guess cannot
   reinforce itself. It also learns syllables the shipped table lacks (names, slang, technical
   words) and that an unmarked word stays unmarked for this user (`ui`, `sen`). Entries are stored
   as strings, so a new shipped table does not break them. One file on the user's machine, with
   clear and pause; nothing is learned in password or private fields.
   - `Personal` in the crate learns runs (a word not known to be right breaks the n-grams around
     it), adds words the table lacks, and saves to a text file of n-grams by spelling. With the same
     learned text it restores exactly like `research.personal` on both tables ("Personal dictionary
     in Rust"). Pausing and private fields are the input method's: it simply does not call `learn`.
   - Through the crate on chat: +3.2 to +3.6 points over the table alone; p99 2.4–2.9 ms per
     syllable ("New words as `<unk>` in context").
5. **Fix syllables that do not exist.** Next, before step 7. In the crate, a typed syllable
   whose unmarked form the table does not know (`khogn`) is replaced by the known form one edit away
   that scores best in context, when it beats the runner-up by a margin of 4; a word in the personal
   dictionary is never a target, and one key undoes the fix. On the small table this changes at most
   0.018% of clean words and is right 98.6–99.6% of the time, fixing 19% (chat) to 46% (subs) of the
   typos it can see ("Fixing syllables the table does not know"). Typos that land on another real
   syllable are left to the spell check (Later). On one writer's real messages it fixed 3 of 17
   typos and changed 2 of 2,430 real words the table lacks, so it is safe but rare ("Fixing unknown
   syllables on real typos"). It runs when a word ends (space or punctuation), since a syllable
   still being typed (`khon` on the way to `không`) is unknown too. Checks: the crate fixes exactly
   what `research.typo` fixes, and p99 per syllable stays under 3 ms with the fix on. It changes the
   word-end result of step 6, so all of step 6's tests and its integration proof run again on it.
6. **Ready for an input method.** Done. Ngó Sen's typing core is already Rust (`bamboo-rs`) and
   holds both readings at a word break (`tét` as interpreted, `test` as typed), so it calls the
   crate as a Rust dependency compiled into its own static library: two Rust static libraries in one
   fcitx5 addon clash on duplicate symbols. A C API waits for a second input method. In this order,
   each a pull request that carries the tests failing without it:
   - **Read the table into memory.** In place of `memmap2`, which Ngó Sen does not vendor, so a
     table file rewritten in place during an update cannot change under a running input method; the
     broken-table tests run on the new path.
   - **Rust 1.88.** `rust-version = "1.88"`, Ngó Sen's minimum, and a CI job on that version.
   - **Link proof.** A local build of Ngó Sen through its own CMake path (vendored crates,
     `--offline --locked`, its release profile with `panic = "abort"`) with the crate as a
     dependency of `bamboo-rs`, calling today's `Table::restore` at a word break; Ngó Sen's core
     tests pass. It proves the build and finds the call sites: `bamboo-rs` ends a word at a space,
     but a run ends at punctuation, digits, symbols and line breaks, as in `research.text.segments`,
     and when the cursor moves. Also chosen here: the source Ngó Sen will vendor the crate from. The
     pull request is the `docs/EXPERIMENTS.md` entry (commands, Ngó Sen commit, results). Where the
     crate's objects live is settled by the steps below and checked again by the integration proof.
   - **Own the table.** `Typing` and `Personal` hold a shared `Table` instead of borrowing one.
     Mechanical; a CHANGELOG line.
   - **One dictionary, a snapshot per run.** Ngó Sen keeps one engine per field, so the personal
     dictionary has one owner for the user, shared by every field; each run reads the snapshot taken
     when it started, and its ids stay valid until it ends. Learning, a clear or a reload makes a
     new snapshot that only later runs see, so a run never mixes two sets of counts. A run started
     after some learning restores exactly like `research.personal` given the same learned text. Ngó
     Sen takes the owner out of its handle registry and releases the registry lock before restoring,
     learning or saving, so no field waits on another. A property test interleaves learn, clear and
     reload across two fields with push, guess and choices.
   - **Never lose the personal file.** A file that fails to load is never overwritten: it stays
     where it is, saving stops, and the crate reports why, so the input method can tell the user and
     offer to start empty, which sets the file aside (an older Ngó Sen meeting a newer file leaves
     it for the newer one to read). Lines dropped on load (a word the table cannot take) are kept and written back.
     A save writes a file readable by the user only, syncs it, renames it into place and syncs the
     directory; one save runs at a time, from the owner, and a save begun before a clear is dropped.
     Tests: an unknown header, a bad line and a refused word each leave the file byte for byte; a
     clear racing a save leaves an empty dictionary on disk; two fields learning then reloading keep
     both.
   - **Word-end contract.** A change is reported as one batch for the run's snapshot: the old
     spelling of the changed part and its new spelling, never a bare length, so the input method
     checks the old part against the field before it deletes, and keeps its own guards (terminals,
     address bars). Where the field does not report its text in time, only the word still being
     typed changes. Backspace into committed words followed by more keys replaces the syllables
     backspaced into. Ngó Sen passes whether the field is private (password, sensitive, a terminal
     hiding what is typed) into `bamboo-rs`, which then does not call the crate; turning private
     ends the run and drops what waited to be learned. Property tests: the part not reported is
     unchanged, output as long as the input, case kept, and several syllables changing at once.
   - **Abuse binary.** Garbage and invalid UTF-8, truncated and corrupt tables and personal files,
     calls in any order: a binary built with Ngó Sen's release profile (`cargo test` ignores
     `panic = "abort"`), and once with overflow checks on. Each case asserts its result (an `Error`,
     a miss, an unchanged file); a control case that panics on purpose must fail, to show the
     harness sees an abort.
   - **Latency, memory and the run cap.** Budgets go in the prediction: p99 under 3 ms per key at
     runs of 50 and 200 syllables, with the personal dictionary; opening the table, loading and
     saving the personal file, each timed alone, off the key path, and Đoán dấu stays off until the
     table is ready; memory for each table and its peak during a reload. The run cap is set from
     these numbers: at the cap a new run starts with the last two syllables as context only, neither
     shown again nor learned twice, and the property and abuse tests cover it in the same pull
     request.
   - **Integration proof.** The link proof again with the final API, through Ngó Sen's word-end and
     private-field paths; Ngó Sen's core tests pass. Done ("Integration proof: the final API inside
     Ngó Sen's core"): 19 of 19 and 129 of 129 tests. For step 7: a change is placed by counting
     words back from the cursor, the keys at a commit lose the key that ended the word before they
     are a second reading, and the new engine calls need the C API before Ngó Sen's lint passes.
7. **Daily use in Ngó Sen.** After step 5. In the Ngó Sen repository, as a feature for its `next`
   branch (its rules keep `main` for releases and `patch` for fixes to the current release), on a
   local build until this repository is public: Đoán dấu as an option, off by default and never in
   private fields, and Cứu chữ's second case (when the text was typed with no marks at all, Tab adds
   them instead of re-reading the keys). Then type with it every day. Counted on the machine, never
   sent: words guessed, guesses changed with Tab, fixes undone. Decided from those counts: whether
   Đoán dấu fills in marks or only suggests them, the confidence below which a guess is shown as
   unsure, and whether the syllable fix can be on by default. These come from one writer, so they
   stay provisional until "measure on my text" results from others agree.

## Before the first public release

- **Licence:** the commercial licence offer and contributor agreement (draft PR #24) wait for a
  lawyer and for the owner and contact details.
- **Repository:** pin the GitHub Actions to commit hashes before the repository goes public.
- **Shipping inside Ngó Sen:** Ngó Sen is GPL-3.0-or-later and vendors its crates for offline
  builds, so a Ngó Sen branch others can see carries the crate's source. This repository must be
  public before then; until it is, step 7 runs on a local build.
- **Model file:** the small table is attached to a GitHub release with its corpus attributions
  (`docs/DATA_SOURCES.md`).

## From users

- **Measure, do not collect.** A "measure on my text" command: the user picks a file of their own
  marked text; their machine strips the marks, restores them and shows the score and the words it got
  wrong. They choose what to send; the text never leaves the machine. All results so far are from one
  writer, and this is how we learn whether they hold for others.
- **No training data from users.** Not raw text, which cannot be anonymized, and not n-gram counts
  either: forum files give more of the same kind of text with no privacy cost.
- Anything sent is shown before sending, sending is off by default, and the sending code lives in this
  repository.

## Later

- **Spell check:** underline a marked word the context disagrees with and suggest the alternative;
  never auto-correct. On chat it catches about half of realistic errors at 0.9% false alarms, mostly
  technical words; the personal dictionary should lower that.
- **Informal writing.** On social media comments restore is right 81% of the time against 92% on
  forums, mostly on informal and southern spellings the corpora rarely write (`lun`, `dị`, `tui`,
  `gòi`), which writers choose on purpose ("Social media comments as a test set"). Fixing it needs
  informal text that may be trained on; ViLexNorm may only test. Ngó Sen already reads the program
  name and the text around the cursor, which could tell a chat box from a document; whether a
  browser tab can be told apart from the browser is not checked yet.
- **Next-word suggestions.** From the table they are too often wrong to show: the next word is among
  three suggestions for 27–34% of words on the corpora (small table; the large reaches 36.5%) and
  14–15% on chat (18% with the personal dictionary); pairs and whole earlier sentences are right
  under 9% and 3% of the time ("Next-word suggestions from the table"). A 7 MB LSTM trained for 4
  hours on this machine's CPU is fast enough (1.4 ms a word) but adds only 1 point on chat and loses
  on wiki and subs ("A small LSTM for next-word suggestions"). Even Gboard has the next word in its
  top 3 for only 27% of words, and suggestions have been measured to slow typing (`PRIOR_WORK.md`).
  Next try, if any: a larger model trained on a rented GPU, which ships only if it clearly beats the
  table on chat.
- **macOS and Windows,** once there is a machine to try typing on them.
