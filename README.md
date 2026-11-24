<div align="center">

# Tim Sen

**Vietnamese diacritic restoration: type without marks, get accented text.**

[![License](https://img.shields.io/badge/license-GPL--3.0--or--later-1f6e5c)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.88%2B-1f6e5c)](crates/timsen)
[![Python](https://img.shields.io/badge/python-3.11%2B-1f6e5c)](pyproject.toml)
[![Status](https://img.shields.io/badge/status-in%20progress-c9a96e)](#current-status)

[First release](#first-release) · [Current status](#current-status) · [How it works](#how-it-works) ·
[Tables & accuracy](#tables-and-accuracy) · [Rust crate](#rust-crate) ·
[Reproducing](#reproducing-the-measurements) · [Licence](#licence)

</div>

---

Tim Sen is the diacritic guesser behind the Đoán dấu feature of the
[Ngó Sen](https://github.com/ngosen/ngosen) input method on Linux: type `toi da go phim` without
marks, get `tôi đã gõ phím`. *Tim sen* is the green heart inside a lotus seed.

This repository holds the research code that trains and measures the model (`research/`) and the
Rust crate that restores marks while typing (`crates/timsen`).

<a id="table-of-contents"></a>

## 📑 Table of contents

- [✨ First release](#first-release)
- [🚦 Current status](#current-status)
- [💡 How it works](#how-it-works)
- [📊 Tables and accuracy](#tables-and-accuracy)
- [🦀 Rust crate](#rust-crate)
- [🔬 Reproducing the measurements](#reproducing-the-measurements)
- [🔒 Privacy](#privacy)
- [📁 Repository layout](#repository-layout)
- [🤝 Contributing](#contributing)
- [🏛️ Licence and attribution](#licence)

<a id="first-release"></a>

## ✨ First release

What a Ngó Sen user on Linux gets:

- **Marks while typing, in every application:** Type without marks, in Telex as usual, or mixed.
  The last few words are restored as you type and may still change. Press `Tab` to change a guess
  or `Esc` to keep what was typed.
- **A personal dictionary:** Learns from words typed with marks and from corrected guesses, on the
  user's machine only.
- **Fixing syllables that do not exist (`khogn` → `không`):** Only when sure, off by default.

What is left out of the first release:

- **Standard Vietnamese only:** Chat is covered when written in full words. Common abbreviations
  (`ko`, `dc`) stay as typed. Informal and regional spellings (`lun`, `dị` for `vậy`, `gòi`) wait.
- **No next-word suggestions:** Syllable n-grams are too often wrong to suggest next words (top-3
  recall is 27–34% on corpora and 14–15% on chat), and suggestions have been shown to slow typing
  down ([`docs/PRIOR_WORK.md`](docs/PRIOR_WORK.md)).
- **No spell check underline:** Underlining words whose context disagrees is deferred.
- **Linux only for now:** macOS and Windows wait until there is a machine to try typing on them.

Nothing is released yet: the crate is not on crates.io, the small table is a draft release, Ngó Sen
does not ship the feature, and there is no C API.

<a id="current-status"></a>

## 🚦 Current status

Progress per step from [`docs/PLAN.md`](docs/PLAN.md):

- **Step 1 · Shipped table (Done):** Binary table format version 2 written by `research.table` with
  n-grams chosen by `research.prune --bytes`. Both small (22.65 MB, default) and large (130.96 MB)
  tables are measured on chat, Wikipedia, subtitles, and forum text
  ([`docs/TABLES.md`](docs/TABLES.md)).
- **Step 2 · Whole-run restore in Rust (Done):** The `timsen` crate (`crates/timsen`) reads
  `.timsen` tables and restores runs of unmarked syllables matching `research.model` output
  exactly, keeping capitalization and supporting old and new tone placement styles.
- **Step 3 · Restore while typing (Done):** `Typing` gives the best spelling after each syllable in
  under 2 ms at p99. `Typing::choices` provides the top three spellings with confidence
  scores; words marked sure (confidence ≥ 0.9) are right 97–98% of the time. Syllables typed with
  marks guide neighboring guesses, and `push_either` weighs raw keys against interpreted readings
  (`tét` vs `test`).
- **Step 4 · Personal dictionary (Done):** `Personal` in the crate learns n-grams exclusively from
  confirmed text (words typed with marks and corrected guesses), preventing errors from
  reinforcing themselves. It adds syllables the table lacks; on chat the small table goes from
  90.61% to 92.91% of words right with it ([`docs/TABLES.md`](docs/TABLES.md)), at a p99 of
  2.4–2.9 ms per syllable.
- **Step 5 · Fix syllables that do not exist (Done):** `Typing::fix` replaces unknown syllables with
  a known syllable one edit away when it beats the runner-up by a margin of 4 (`FIX_MARGIN`).
  Decided at word end, it is right 98.0–99.5% of the time and fixes 23–25% of typos it can see. Off
  by default; `Run::undo_fix` takes the latest fix back, so one key undoes it.
- **Step 6 · Ready for an input method (Done):** Table files are read entirely into memory on open
  (no `memmap2`). Crate targets Rust 1.88 minimum. `Dictionary` provides snapshot isolation across
  fields so runs never mix counts. Atomic file saves protect personal dictionaries from corruption.
  `Run` yields batched `Change` structs reporting old and new text before deletion. Caps runs at
  200 syllables (`MAX_RUN`). Abuse binaries and integration proof inside Ngó Sen's core pass (19 of
  19 and 139 of 139 tests).
- **Step 7 · Daily use in Ngó Sen (Next):** Prepared in a local copy, Ngó Sen itself untouched.
  Left to do there: the calls that open the table and the shared personal dictionary, applying
  changes after each key, undoing a fix with Backspace, and the Đoán dấu option, off by default.
  Then daily typing decides whether it fills in marks or only suggests them.

<a id="how-it-works"></a>

## 💡 How it works

- **Language model:** Syllable 3-grams with stupid backoff (factor 0.4) and a leftover backoff
  penalty (`LEFTOVER = 0.5`) that charges more when backing off from contexts the table kept nearly
  whole.
- **Candidates:** For each typed syllable, the table lists every accented spelling it has seen
  (`go` → `gõ`, `gỗ`, `gỡ`, …).
- **Search:** A Viterbi search picks the combination of spellings whose sequences were seen most
  often. Each new syllable adds one step, so the best spelling so far is ready after every key;
  words three syllables back are as good as final.
- **Context anchors:** Words typed with explicit marks are kept as typed and serve as fixed context
  anchors that steer guesses for adjacent words (improving nearby word accuracy by 0.7–1.4 points).
- **Personal dictionary:** Adds syllable 2- and 3-gram counts from confirmed text. A dynamic weight
  (`min(3000, table total / tokens learned)`) falls as the dictionary grows, so the user's counts
  do not drown the table's.

<a id="tables-and-accuracy"></a>

## 📊 Tables and accuracy

The two tables use the same binary format and work with the same personal dictionary:

| Test set | Small table (default) | Large table |
| :--- | :--- | :--- |
| File size | 22.65 MB | 130.96 MB |
| Chat + personal | 92.91% | 92.78% |
| Chat | 90.61% | 90.65% |
| Wikipedia | 96.03% | 97.15% |
| Subtitles | 95.73% | 96.59% |
| Forum | 93.26% | 94.30% |

All figures are from "Forum pages from every FineWeb-2 file" in
[`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md):

- **Test sets:** `wiki` (4,000 sentences, 73,604 words), `subs` (4,000 sentences, 31,845 words),
  and `forum` (4,000 sentences, 92,220 words) are frozen held-out sets. `chat` is 2,604 sentences
  from one writer's messages, so it may differ for other people.
- **Training data:** Both tables are trained on Wikipedia, OpenSubtitles, FineWeb-2 forum files 1–4,
  and technology forums from files 1–29 (`python -m research.train MODEL.npz wiki subs forum tech`).
- **Vocabulary pruning:** Both tables leave out unmarked words seen fewer than 1,000 times whose
  only spelling is themselves (`--min-plain 1000`), leaving English words and typos to restore as
  typed without wasting table entries.
- **Choosing a table:** On chat with the personal dictionary, the small table matches the large
  table (92.91% vs 92.78%). On edited prose, the large table gets about one more word in 100 right
  (96.03% vs 97.15% on Wikipedia). The small table ships first as the default; the large table is an
  option for users who mostly write long edited documents.
- **Memory footprint:** The table file is read entirely into memory on open (~40 ms), occupying
  about 31 MB of RAM for the small table once touched.

<a id="rust-crate"></a>

## 🦀 Rust crate

The Rust crate lives in [`crates/timsen`](crates/timsen). It requires Rust 1.88 or newer (edition
2024). It is not published on crates.io yet; include it as a path or git dependency.

### Restoring a full run

To restore a slice of unaccented words at once:

```rust
use timsen::{Table, ToneStyle};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Open the small binary table (22.65 MB)
    let table = Table::open("small.timsen")?;

    // Restore unaccented syllables
    let words = ["toi", "da", "go", "phim"];
    let restored = table.restore(&words, ToneStyle::New);
    assert_eq!(restored.join(" "), "tôi đã gõ phím");

    Ok(())
}
```

### Interactive typing with personal learning

For input methods handling keystrokes and personal dictionary counts:

```rust
use std::sync::Arc;
use timsen::{Dictionary, Table, ToneStyle};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let table = Arc::new(Table::open("small.timsen")?);
    let mut dict = Dictionary::new(table);

    // Learn from a run known to be correct (typed with marks or confirmed)
    dict.learn(&[Some("tôi"), Some("đã"), Some("gõ"), Some("phím")]);

    // Start a typing session for an input field
    let mut typing = dict.typing();
    for syllable in ["toi", "da", "go", "phim"] {
        typing.push(syllable);
    }

    let guess = typing.finish(ToneStyle::New);
    assert_eq!(guess.join(" "), "tôi đã gõ phím");

    Ok(())
}
```

<a id="reproducing-the-measurements"></a>

## 🔬 Reproducing the measurements

Requires Python 3.11 or newer. Data goes to `TIMSEN_DIR` (default `/tmp/timsen`); expect a few GB:

```bash
pip install -e '.[dev]'
python -m research.fetch_wiki                 # Wikipedia, CC BY-SA
python -m research.fetch_subs                 # OpenSubtitles, counts ship with attribution
python -m research.fetch_fineweb forum 1      # forum pages from FineWeb-2 file 1 (repeat for 2-4)
python -m research.fetch_fineweb tech 1       # technology forums from file 1 (repeat for 2-29)
python -m research.train /tmp/timsen/models/wsft.npz wiki subs forum tech
python -m research.evaluate /tmp/timsen/models/wsft.npz \
    /tmp/timsen/test/wiki /tmp/timsen/test/forum
```

To build the small and large shipped tables:

```bash
python -m research.prune /tmp/timsen/models/wsft.npz small.timsen --bytes 22650896 --min-plain 1000
python -m research.prune /tmp/timsen/models/wsft.npz large.timsen --bytes 130958840 --min-plain 1000
```

To measure on your own writing, put your messages in a text file (one per line) and run:

```bash
python -m research.chat_testset FILE
```

The resulting test set stays on your machine. Corpus licences are listed in
[`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

<a id="privacy"></a>

## 🔒 Privacy

- **Fully on-device:** All computation happens locally on the user's computer. Keystrokes, text,
  and n-gram counts never leave the machine.
- **Local dictionary storage:** The personal dictionary is stored in a single text file readable
  only by the user.
- **Private fields:** Nothing is guessed or learned in password and other private fields; the input
  method does not call the crate there.
- **Local evaluation:** A test set built from your own messages with `research.chat_testset` stays
  on the machine. The crate sends nothing; the plan is a "measure on my text" command whose score
  the user may choose to send ([`docs/PLAN.md`](docs/PLAN.md), "From users").
- **No private text in git:** In accordance with [`AGENTS.md`](AGENTS.md), private writing is
  never committed or quoted in documentation, pull requests, or code.

<a id="repository-layout"></a>

## 📁 Repository layout

- [`crates/timsen`](crates/timsen): Rust library implementing table loading, typing lattice,
  personal dictionary, and word-end change contracts.
- `research/`: Python scripts for corpus acquisition, n-gram counting, table pruning, evaluation,
  and test set construction.
- `docs/`: Technical documentation and project records:
  - [`docs/PLAN.md`](docs/PLAN.md): Implementation steps and milestone status.
  - [`docs/TABLES.md`](docs/TABLES.md): Table size benchmarks and accuracy comparisons.
  - [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md): Empirical log of every tested hypothesis.
  - [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md): Corpora origins, licensing terms, and filters.
  - [`docs/PRIOR_WORK.md`](docs/PRIOR_WORK.md): Literature survey on predictive typing
    and accent restoration.
- `tests/`: Tests of the research code (`python -m pytest`). The crate's own tests, including the
  check against the Python model on a fixture table, are in `crates/timsen/tests`.

<a id="contributing"></a>

## 🤝 Contributing

See [`AGENTS.md`](AGENTS.md) for contribution guidelines:

- Every change goes through a pull request into `main` with passing CI checks.
- Measurements must have predictions recorded in [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) before
  running the experiment.
- Private text must never enter the repository.
- English only for identifiers, comments, commit messages, PR descriptions, and documentation.

<a id="licence"></a>

## 🏛️ Licence and attribution

Code is licensed under GPL-3.0-or-later ([`LICENSE`](LICENSE)).

Released count tables follow the licences of their corpora
([`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md)):

- Wikipedia: CC BY-SA 4.0; the released table is CC BY-SA 4.0.
- FineWeb-2: ODC-By 1.0, plus the Common Crawl terms of use.
- OpenSubtitles (<http://www.opensubtitles.org/>, via [OPUS](https://opus.nlpl.eu/); P. Lison and
  J. Tiedemann, 2016, "OpenSubtitles2016: Extracting Large Parallel Corpora from Movie and TV
  Subtitles", LREC 2016). No formal licence; a release ships counts only, never text.
