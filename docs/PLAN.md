# Plan

From research code to a library input methods can use. Each step is one or more pull requests with
tests, and each measurement goes into [`EXPERIMENTS.md`](EXPERIMENTS.md) with its prediction.

## Decisions

- **Model:** syllable 3-grams with stupid backoff, in two tables of the same format: small (3-grams
  seen 50+ times, 2-grams 20+; 22.6 MB) and large (5+, 3+; 130.7 MB). Both leave out unmarked words
  seen fewer than 1,000 times whose only spelling is themselves. With the personal dictionary they
  differ by 0.23 points on chat (92.20% and 92.43%, "New words as `<unk>` in context"); on edited
  prose by about 1.7 (wiki 94.84% and 96.55%). The small table ships first; the large one is added
  later if users ask for better accuracy on longer writing. Kneser-Ney at the same sizes gains
  0.3–0.5 points on edited prose and 0–0.3 on chat, but cannot take personal counts by simple
  addition; revisit only with a measured way to combine it with the personal dictionary.
- **Corpora:** Wikipedia, OpenSubtitles and FineWeb-2 forum pages. OpenSubtitles has no formal
  licence; the tables ship its counts with attribution, as `wordfreq` does, and are rebuilt without
  it if a takedown request comes (`docs/DATA_SOURCES.md`).
- **Where the gain is:** the personal dictionary (+3.2 to +3.6 points on chat depending on the
  table, measured after the total fix; it was still rising with more learned text before that fix,
  not rerun since) and revising the last few words while typing (89% against 80% when each word is
  fixed as typed). More general text gives about half a point per doubling.
- **More general text comes from more forum files, not from users.** Counts donated by users would be
  a small forum with a privacy cost; the personal dictionary gains because the text is the user's own.
  The only thing taken from users is a score measured on their machine (see "From users").
- **Abbreviations stay as typed.** `ko`, `e`, `ok`, `j`, `b` are already kept right, since the forum
  text uses them. `a` is marked wrongly 22% of the time, but forcing it would break `ạ` and `à` about
  as often. Expanding them (`ko` → `không`) is the input method's macro table, opt-in.
- **Standard Vietnamese first.** The first release restores marks and fixes wrong syllables in
  standard spelling, chat included when it is written in full words. Informal spellings (`lun`,
  `dị` for `vậy`, `gòi`) wait; see "Informal writing" under Later.

## Steps

1. **Shipped table.** Done: `research.table` writes the fixed binary format, and both tables are
   measured on all test sets, alone and with the personal dictionary (`docs/EXPERIMENTS.md`, "Pruned
   table for shipping" and "Trimming the table vocabulary").
2. **Whole-run restore in Rust.** Done: the `timsen` crate (`crates/timsen`) maps a table and
   restores a run, keeping the user's capitalization and following the tone placement setting. It
   restores every run of every test set exactly like `research.model` on both tables
   (`docs/EXPERIMENTS.md`, "Rust restore against the Python model"); CI checks it on a small fixture
   table.
3. **Restore while typing.** After each syllable, return the best spelling of the last few words
   (earlier guesses may change), a confidence per word and the top three choices for unsure words.
   Target: a few milliseconds per key on a typical laptop.
   - Done: `Typing` in the crate gives the best spelling after each syllable in under 2 ms at p99;
     words three syllables back are as good as final ("Restoring while typing" in
     `EXPERIMENTS.md`).
   - Done: `Typing::choices` gives the top three spellings and a confidence per word. At 0.9, a
     newly shown word marked sure is right 97–98% of the time, and over 90% of the words that later
     change were below 0.9 when shown ("Confidence and choices while typing").
   - Done: a syllable typed with marks is kept as typed and serves as context for the guessed ones
     (0.7–1.4 points better next to them). `push_either` takes both readings of a word, as
     interpreted (`tét`) and as raw letters (`test`); the library knows nothing about Telex or VNI.
     Typed in Telex through the Ngó Sen engine, switching to the raw reading at confidence 0.99
     fixes 21–153 words per test set and breaks none; below that the raw reading is only a
     suggestion ("Marked words and two readings").
   - Rejecting a guess uses the same keys as Cứu chữ: Tab to change, Esc to keep.
4. **Personal dictionary.** Learn syllable 2- and 3-gram counts only from text known to be right:
   words the user typed with marks, and guesses the user corrected. Guesses left untouched are not
   learned, so a wrong guess cannot reinforce itself. It also learns syllables the shipped table lacks
   (names, slang, technical words) and that an unmarked word stays unmarked for this user (`ui`,
   `sen`). Entries are stored as strings, so a new shipped table does not break them. One file on the
   user's machine, with clear and pause; nothing is learned in password or private fields. Check:
   rebuilding the five-fold chat measurement through the library gives about the same gain as
   `research.personal`.
   - Done: `Personal` in the crate learns runs (a word not known to be right breaks the n-grams
     around it), adds words the table lacks, and saves to a text file of n-grams by spelling. With
     the same learned text it restores exactly like `research.personal` on both tables ("Personal
     dictionary in Rust"). Pausing and private fields are the input method's: it simply does not
     call `learn`.
   - Measured through the crate on chat: +3.2 to +3.6 points over the table alone, equal to
     `research.personal` once learned words the table lacks are scored as its `<unk>`; p99 2.4–2.9
     ms per syllable ("New words as `<unk>` in context").
5. **Fix syllables that do not exist.** In the crate, a typed syllable whose unmarked form the
   table does not know (`khogn`) is replaced by the known form one edit away that scores best in
   context, when it beats the runner-up by a margin of 4; a word in the personal dictionary is never
   a target, and one key undoes the fix. On the small table this changes at most 0.018% of clean
   words and is right 98.6–99.6% of the time, fixing 19% (chat) to 46% (subs) of the typos it can
   see ("Fixing syllables the table does not know"). Typos that land on another real syllable are
   left to the spell check below. On one writer's real messages it fixed 3 of 17 typos and changed
   2 of 2,430 real words the table lacks, so it is safe but rare ("Fixing unknown syllables on real
   typos"); it ships off by default until daily use shows how often a fix is undone. Check: the crate
   fixes exactly what `research.typo` fixes.
6. **C API.** A thin C interface and header so Linux input methods can use the crate: restore while
   typing, the fix above, the personal dictionary. macOS and Windows are set aside until there is a
   machine to try typing on them.

Then, in the Ngó Sen repository: an option, off by default. Whether it fills in marks or only suggests
is decided after using it. Cứu chữ gets a second case: when the text was typed with no marks at all,
Tab adds them with Đoán dấu instead of re-reading the keys.

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

- **Next-word suggestions.** From the table they are too often wrong to show: the next word is among
  three suggestions for 27–34% of words on the corpora and 14–15% on chat (18% with the personal
  dictionary); pairs and whole earlier sentences are right under 9% and 3% of the time ("Next-word
  suggestions from the table"). A 7 MB LSTM trained for 4 hours on this machine's CPU is fast enough
  (1.4 ms a word) but adds only 1 point on chat and loses on wiki and subs ("A small LSTM for
  next-word suggestions"). Next try, if any: a larger model trained on a rented GPU, which ships only
  if it clearly beats the table on chat at a size and speed fit for typing.
- **Spell check:** underline a marked word the context disagrees with and suggest the alternative;
  never auto-correct. On chat it catches about half of realistic errors at 0.9% false alarms, mostly
  technical words; the personal dictionary should lower that.
- **Informal writing.** On social media comments restore is right 81% of the time against 92% on
  forums, mostly on informal and southern spellings the corpora rarely write (`lun`, `dị`, `tui`,
  `gòi`), which writers choose on purpose ("Social media comments as a test set"). Fixing it needs
  informal text that may be trained on; ViLexNorm may only test. Ngó Sen already reads the program
  name and the text around the cursor, which could tell a chat box from a document; whether a
  browser tab can be told apart from the browser is not checked yet.
