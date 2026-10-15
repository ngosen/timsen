# AGENTS.md

Rules for anyone (human or coding agent) changing this repository. Most work here is done with an AI
coding agent; the output must still read like a careful human wrote it, and the person sending it must
be able to explain every line.

This repository holds Tim Sen, the diacritic guesser behind the Đoán dấu feature of the
[Ngó Sen](https://github.com/ngosen/ngosen) input method: type `toi da go phim`, get `tôi đã gõ phím`. It holds the research code that trains
and measures the model (`research/`) and the Rust crate that restores marks from a table
(`crates/timsen`). A C API, usable from input methods on Linux, macOS and Windows, comes later.

## Before you start

- Read the current state from the repository, not from memory: `git status`, open PRs, and the latest
  entries in [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md).
- Check which corpora and test sets a result used before comparing it with another one. Two numbers
  are comparable only on the same test file.

## Measuring

Every number in this repository says what was measured, on which test set, with which command.

- **Write the prediction first.** Before running a measurement, add the expected result to the
  experiment's entry in `docs/EXPERIMENTS.md`. After the run, record the result next to it, including
  when it missed. A number read before predicting proves nothing.
- **Held-out text never trains.** Each fetch script removes its test sentences from the training data.
  Keep it that way when adding a corpus.
- **Show the instrument can see the effect.** A "no change" result needs a check that the change was
  actually applied (for example, a model file that differs, a vocabulary size that moved).
- **Compare like with like.** Freeze a test file (copy it) before a series of runs. Results on a test
  set that changed in between are not comparable.
- **Prefer realistic errors.** Synthetic errors drawn uniformly are easier than real typing mistakes;
  report the realistic variant (`spellcheck.py --weighted`), or both.

## Privacy and data

- **Never commit anyone's own writing.** `research/chat_testset.py` builds a test set from a file the
  user supplies; that file and `test/chat` stay on their machine. Do not quote sentences from it in
  docs, commits, issues or PRs; quote counts and word pairs only.
- **Track licences.** Every corpus is listed in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) with
  its licence and whether counts derived from it may ship. Add the entry in the same PR that adds the
  fetch script.
- **Data stays out of git.** Corpora, test sets and models live under `TIMSEN_DIR` (default
  `/tmp/timsen`, RAM on the dev machine). Released models are attached to GitHub releases.
- **Keep throwaway data in RAM.** Gigabytes of rewritten corpora wear out an SSD. Delete models you
  no longer compare against; watch free memory before a large training run (a 700M-token model peaks
  near 27 GB).

## Code

- **English only** for identifiers, comments, docs, commit messages and PR text.
- **Comments say why, not what.** Most are one line. No measurements, dates or history in code; those
  go in `docs/EXPERIMENTS.md`, the commit message or the PR.
- **Reuse what exists.** Tokenizing and mark handling live in `research/text.py`; the model in
  `research/model.py`. Do not copy them into a new script.
- **Style:** `ruff format` and `ruff check` (config in `pyproject.toml`). Functions under ~50 lines.
- **Rust:** `cargo fmt`, `cargo clippy --all-targets -- -D warnings`, `cargo test`. The crate must
  restore exactly like `research.model`; after changing the table format or the model, rebuild the
  test table with `python -m research.fixture`.
- **Tests:** `python -m pytest`. A bug fix comes with a test that fails without it.

## Commits and pull requests

- Every change goes through a PR into `main`; CI (ruff, pytest) must pass. GitHub does not enforce
  this on a private repository, so do not push to `main` directly.
- Once CI passes on the PR's latest commit, the agent may merge it (merge commit, branch deleted)
  without waiting for review.
- Conventional Commits, imperative subject of at most 72 characters: `feat(research): add forum corpus`.
  The body says what changed and why; numbers go one per line with how they were measured.
- One concern per PR. An experiment's code and its `docs/EXPERIMENTS.md` entry go together.
- Before committing, read the full diff: no data files, no private text, no unrelated changes.
- Keep the `Co-Authored-By:` trailer the agent adds. It is how we disclose AI assistance.
- Add a line to [`CHANGELOG.md`](CHANGELOG.md) under `## Unreleased` for changes a user of the
  library or of the released model would notice.
