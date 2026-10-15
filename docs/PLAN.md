# Plan

From research code to a library input methods can use. Each step is one or more pull requests with
tests, and each measurement goes into [`EXPERIMENTS.md`](EXPERIMENTS.md) with its prediction.

## Decisions

- **Model:** syllable 3-grams with stupid backoff, pruned to 30–40 MB. Kneser-Ney gained about one
  point at 1.5 GB, but nobody has measured it at the size an input method can ship; revisit only with
  an equal-size comparison.
- **Corpora:** Wikipedia, OpenSubtitles and FineWeb-2 forum pages. The OpenSubtitles licence must be
  settled before the repository or the table is made public.
- **Where the gain is:** the personal dictionary (+3.4 points on chat, still rising) and revising the
  last few words while typing (89% against 80% when each word is fixed as typed). More general text
  gives about half a point per doubling and is not pursued now.

## Steps

1. **Shipped table.** Build the pruned table and a fixed binary format the library can map from disk
   without parsing. Measure the shipped table on all test sets.
2. **Whole-run restore in Rust.** A Rust crate reads the table and restores a run. On the same table
   it must give exactly the same output as `research.model` on every test set.
3. **Restore while typing.** After each syllable, return the best spelling of the last few words
   (earlier guesses may change), a confidence per word and the top three choices for unsure words.
   Target: a few milliseconds per key on a typical laptop.
   The input method also passes the keys typed, so a word like `test` (Telex gives `tét`, a valid
   syllable) can be kept as typed when the context favours the English word. Measure fixes and wrong
   changes before shipping; when unsure, keep the word or only suggest.
4. **Personal dictionary.** Learn syllable 2- and 3-gram counts only from text known to be right:
   words the user typed with marks, and guesses the user corrected. Guesses left untouched are not
   learned, so a wrong guess cannot reinforce itself. Stored in one file on the user's machine,
   with clear and pause; nothing is learned in password or private fields. Check: rebuilding the
   five-fold chat measurement through the library gives about the same gain as `research.personal`.
5. **C API.** A thin C interface and header so input methods on macOS and Windows can use the crate.

Then, in the Ngó Sen repository: an option, off by default. Whether it fills in marks or only suggests
is decided after using it.

## Later

- **Spell check:** underline a marked word the context disagrees with and suggest the alternative;
  never auto-correct. On chat it catches about half of realistic errors at 0.9% false alarms, mostly
  technical words; the personal dictionary should lower that.
