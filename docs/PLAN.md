# Plan

From research code to a library input methods can use. Each step is one or more pull requests with
tests, and each measurement goes into [`EXPERIMENTS.md`](EXPERIMENTS.md) with its prediction.

## Decisions

- **Model:** syllable 3-grams with stupid backoff, in two tables of the same format: small (3-grams
  seen 50+ times, 2-grams 20+; 22.6 MB) and large (5+, 3+; 130.7 MB). Both leave out unmarked words
  seen fewer than 1,000 times whose only spelling is themselves. With the personal dictionary they
  differ by 0.27 points on chat (92.05% and 92.32%); on edited prose by about 1.7 (wiki 94.84% and
  96.55%). The small table ships first; the large one is added later if users ask for better
  accuracy on longer writing. Kneser-Ney gained about one point at 1.5 GB but is unmeasured at these
  sizes; revisit only with an equal-size comparison.
- **Corpora:** Wikipedia, OpenSubtitles and FineWeb-2 forum pages. The OpenSubtitles licence must be
  settled before the repository or the table is made public.
- **Where the gain is:** the personal dictionary (+2.7 to +3.4 points on chat depending on the table, still rising) and revising the
  last few words while typing (89% against 80% when each word is fixed as typed). More general text
  gives about half a point per doubling.
- **More general text comes from more forum files, not from users.** Counts donated by users would be
  a small forum with a privacy cost; the personal dictionary gains because the text is the user's own.
  The only thing taken from users is a score measured on their machine (see "From users").
- **Abbreviations stay as typed.** `ko`, `e`, `ok`, `j`, `b` are already kept right, since the forum
  text uses them. `a` is marked wrongly 22% of the time, but forcing it would break `ạ` and `à` about
  as often. Expanding them (`ko` → `không`) is the input method's macro table, opt-in.

## Steps

1. **Shipped table.** Done: `research.table` writes the fixed binary format, and both tables are
   measured on all test sets, alone and with the personal dictionary (`docs/EXPERIMENTS.md`, "Pruned
   table for shipping" and "Trimming the table vocabulary").
2. **Whole-run restore in Rust.** A Rust crate reads the table and restores a run. On the same table
   it must give exactly the same output as `research.model` on every test set. Output keeps the
   user's capitalization and follows the input method's tone placement setting (the table is built
   with the new placement).
3. **Restore while typing.** After each syllable, return the best spelling of the last few words
   (earlier guesses may change), a confidence per word and the top three choices for unsure words.
   Target: a few milliseconds per key on a typical laptop.
   - Mixed input: a syllable the user typed with marks is kept as typed; only unmarked syllables are
     guessed.
   - The input method passes both readings of a word, as interpreted (`tét`) and as raw letters
     (`test`); the library chooses between them from context, so it knows nothing about Telex or VNI.
     Measure fixes and wrong changes before shipping; when unsure, keep the word or only suggest.
   - Rejecting a guess uses the same keys as Cứu chữ: Tab to change, Esc to keep.
4. **Personal dictionary.** Learn syllable 2- and 3-gram counts only from text known to be right:
   words the user typed with marks, and guesses the user corrected. Guesses left untouched are not
   learned, so a wrong guess cannot reinforce itself. It also learns syllables the shipped table lacks
   (names, slang, technical words) and that an unmarked word stays unmarked for this user (`ui`,
   `sen`). Entries are stored as strings, so a new shipped table does not break them. One file on the
   user's machine, with clear and pause; nothing is learned in password or private fields. Check:
   rebuilding the five-fold chat measurement through the library gives about the same gain as
   `research.personal`.
5. **C API.** A thin C interface and header so input methods on macOS and Windows can use the crate.

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

- **Spell check:** underline a marked word the context disagrees with and suggest the alternative;
  never auto-correct. On chat it catches about half of realistic errors at 0.9% false alarms, mostly
  technical words; the personal dictionary should lower that.
