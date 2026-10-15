# Changelog

All notable changes to Tim Sen. The format follows [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Changed

- `docs/PLAN.md`, `docs/TABLES.md`: the small table ships first; stupid backoff stays after measuring
  Kneser-Ney at the shipped sizes (#11).
- `docs/PLAN.md`: two shipped tables, 44 MB and 177 MB, chosen by the user (#9).
- `docs/PLAN.md`: mixed marked/unmarked input, both readings of a word, abbreviations kept as typed,
  new words in the personal dictionary, and what is taken from users (#5).

### Added

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
