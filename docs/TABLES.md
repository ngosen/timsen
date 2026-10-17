# Choosing a table

Tim Sen has two tables in the same file format, used with the same personal dictionary. **The small
table is the default**, and the one the first release ships; the large one is an option for people
who mostly write long edited text.

| | Small (default) | Large |
| --- | --- | --- |
| File | 22.65 MB | 130.96 MB |
| Chat + personal | 92.91% | 92.78% |
| Chat | 90.61% | 90.65% |
| Wikipedia | 96.03% | 97.15% |
| Subtitles | 95.73% | 96.59% |
| Forum | 93.26% | 94.30% |

On chat the small table is as good as the large one; on edited prose the large one gets about one
more word in 100 right.

Both are built from the model trained on Wikipedia, subtitles, forum pages from FineWeb-2 files 1
to 4 and technology forums from files 1 to 29 (`python -m research.train MODEL.npz wiki subs forum
tech`), in format version 2:

```
python -m research.prune MODEL.npz small.timsen --bytes 22650896 --min-plain 1000
python -m research.prune MODEL.npz large.timsen --bytes 130958840 --min-plain 1000
```

All figures are from "Forum pages from every FineWeb-2 file" in [`EXPERIMENTS.md`](EXPERIMENTS.md);
chat is 2,604 sentences from one writer, so it may differ for other people, the others are the
frozen test files. How each step got here, from the count-pruned tables of 2026-10-15: choosing n-grams by weight ("Keeping the n-grams that matter instead of the frequent ones"), the
leftover backoff ("Backoff that knows how much of a context was pruned"), the personal weight 1000
("Tuning the personal dictionary weight"), the denser format ("A denser table file") and the
technology forums ("A technology-forum slice"; forum pages from the other files made it worse).

They differ in how many rare word sequences they keep. Both leave out unmarked words seen fewer than
1,000 times whose only spelling is themselves (English words, typos); those are restored as typed
either way, and leaving them out cost nothing measurable ("Trimming the table vocabulary" in
[`EXPERIMENTS.md`](EXPERIMENTS.md)).

## How the sizes were chosen

The two sizes were chosen on 2026-10-15 from tables pruned by count, in format version 1 and before
the trimming above, so the sizes and figures below are older than the ones at the top; the two
chosen levels are in bold.

| File | 3-word ≥ | 2-word ≥ | Chat + personal | Chat | Wikipedia | Forum |
| --- | --- | --- | --- | --- | --- | --- |
| 1.5 GB (unpruned) | 1 | 1 | 91.79% | 89.13% | 97.61% | 94.47% |
| 278 MB | 3 | 2 | 92.23% | 89.24% | 96.94% | 94.02% |
| **177 MB** (large) | 5 | 3 | 92.16% | 89.00% | 96.58% | 93.76% |
| 108 MB | 10 | 5 | 92.06% | 88.90% | 96.06% | 93.21% |
| 68 MB | 20 | 10 | 91.96% | 88.59% | 95.57% | 92.55% |
| 51 MB | 30 | 20 | 91.87% | 88.43% | 95.10% | 92.13% |
| **44 MB** (small) | 50 | 20 | 91.81% | 88.41% | 94.82% | 91.82% |
| 38 MB | 50 | 50 | 91.68% | 88.05% | 94.52% | 91.48% |

Each figure is the share of words restored exactly after every mark is removed. "3-word ≥" and
"2-word ≥" are how many times a sequence must appear in the training text to be kept. The test sets
are described in [`EXPERIMENTS.md`](EXPERIMENTS.md); the chat set is one writer's messages, so the
chat figures may differ for other people.

What the table shows:

- **Chat with the personal dictionary barely depends on size.** Every table is within half a point,
  and the pruned ones from 108 MB up do better than the unpruned model.
- **Edited prose does.** Each step up adds about half a point on Wikipedia and forum text, where the
  personal dictionary helps less.

At the time the large table got about 1.7 more words in 100 right on edited prose; since weighted
pruning and the denser format, the gap is about one word in 100.

The file is mapped from disk, so only the parts in use are read into memory; the size mainly affects
the download.

Measured on 2026-10-15 with `research.evaluate` and `research.personal` (5-fold, weight 100); see
"Pruned table for shipping" in [`EXPERIMENTS.md`](EXPERIMENTS.md).
