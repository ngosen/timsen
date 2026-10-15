# Changelog

All notable changes to Đoán dấu. The format follows [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Added

- `research.train --order 4`: stupid-backoff 4-grams, kept for comparison with Kneser-Ney (#3).
- `research.kn_export` and `research.kn_model`: Kneser-Ney models estimated with KenLM, read from
  ARPA and scored with beam search (#2).
- `research.typing_sim`: accuracy when words are fixed as typed, and how often the model could ask
  instead of guessing (#1).
- Research code to train a syllable trigram model from Wikipedia, OpenSubtitles and FineWeb-2 and to
  measure diacritic restoration, context spell checking and a personal dictionary.
