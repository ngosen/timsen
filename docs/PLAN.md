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
2. **Whole-run restore in Rust.** Done: the `timsen` crate (`crates/timsen`) maps a table and
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
     Typed in Telex through the Ngó Sen engine, switching to the raw reading at confidence 0.99
     fixes 21–153 words per test set and breaks none; below that the raw reading is only a
     suggestion ("Marked words and two readings").
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
5. **Fix syllables that do not exist.** Next. In the crate, a typed syllable whose unmarked form the
   table does not know (`khogn`) is replaced by the known form one edit away that scores best in
   context, when it beats the runner-up by a margin of 4; a word in the personal dictionary is never
   a target, and one key undoes the fix. On the small table this changes at most 0.018% of clean
   words and is right 98.6–99.6% of the time, fixing 19% (chat) to 46% (subs) of the typos it can
   see ("Fixing syllables the table does not know"). Typos that land on another real syllable are
   left to the spell check (Later). On one writer's real messages it fixed 3 of 17 typos and changed
   2 of 2,430 real words the table lacks, so it is safe but rare ("Fixing unknown syllables on real
   typos"). It runs when a word ends (space or punctuation), since a syllable still being typed
   (`khon` on the way to `không`) is unknown too. Checks: the crate fixes exactly what
   `research.typo` fixes, and p99 per syllable stays under 3 ms with the fix on.
6. **C API.** A thin C interface and header so Linux input methods can use the crate: restore while
   typing, the fix above, the personal dictionary.
7. **Daily use in Ngó Sen.** In the Ngó Sen repository: Đoán dấu as an option, off by default, and
   Cứu chữ's second case (when the text was typed with no marks at all, Tab adds them instead of
   re-reading the keys). Then type with it every day. Counted on the machine, never sent: words
   guessed, guesses changed with Tab, fixes undone. Decided from those counts: whether Đoán dấu fills
   in marks or only suggests them, the confidence below which a guess is shown as unsure, and
   whether the syllable fix can be on by default. These come from one writer, so they stay
   provisional until "measure on my text" results from others agree.

## Before the first public release

- **Licence:** the commercial licence offer and contributor agreement (draft PR #24) wait for a
  lawyer and for the owner and contact details.
- **Repository:** pin the GitHub Actions to commit hashes before the repository goes public.
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
