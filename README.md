# Tim Sen

Diacritic guessing for Vietnamese input methods: type `toi da go phim` without marks, get
`tôi đã gõ phím`. Built for the [Ngó Sen](https://github.com/ngosen/ngosen) input method, where the
feature is called Đoán dấu. *Tim sen* is the green heart inside a lotus seed.

**Status: research.** This repository holds the code that trains and measures the model
(`research/`) and the Rust crate that restores marks from a table (`crates/timsen`). A C API, so input
methods on Linux, macOS and Windows can use it, comes later. Results so far are in
[`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md); the steps ahead are in [`docs/PLAN.md`](docs/PLAN.md).
How the two tables (22.6 MB, shipped first, and 130.7 MB) compare is in
[`docs/TABLES.md`](docs/TABLES.md).

## How it works

The model counts which syllables follow which in a large body of correctly accented text (1-, 2- and
3-syllable sequences). To restore a sentence, it lists every accented spelling of each typed syllable
(`go` → gõ, gỗ, gỡ, …) and picks the combination whose sequences were seen most often. Counts from the
user's own typing can be added on top, which matters most for technical and chat vocabulary.

## Reproducing the measurements

Python 3.11+. Data goes to `TIMSEN_DIR` (default `/tmp/timsen`); expect a few GB.

```bash
pip install -e '.[dev]'
python -m research.fetch_wiki                 # Wikipedia, CC BY-SA
python -m research.fetch_subs                 # OpenSubtitles, research only
python -m research.fetch_fineweb forum 1      # forum pages from FineWeb-2 file 1 (repeat for 2-4)
python -m research.train /tmp/timsen/models/wsf.npz wiki subs forum
python -m research.evaluate /tmp/timsen/models/wsf.npz /tmp/timsen/test/wiki /tmp/timsen/test/forum
```

To measure on your own writing, put your messages in a text file (one per line) and run
`python -m research.chat_testset FILE`; the test set stays on your machine. Corpus licences are listed
in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## Contributing

See [`AGENTS.md`](AGENTS.md): measurements carry their prediction and test set, private text never
enters the repository, and every change goes through a pull request with passing CI.

## Licence

Code: GPL-3.0-or-later. Released count tables follow the licences of their corpora
([`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md)).
