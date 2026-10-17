# Changelog

All notable changes to Tim Sen. The format follows [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Changed

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
