# Choosing a table

Tim Sen ships two tables of word counts, **44 MB** and **177 MB**. Both use the same file format and
the same personal dictionary; they differ in how many rare word sequences they keep. The other sizes
below were measured to choose them and are not shipped.

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

So: the small table for mostly chatting; the large one for articles, documents or long emails, where
it gets about 1.8 more words in 100 right.

The file is mapped from disk, so only the parts in use are read into memory; the size mainly affects
the download.

Measured on 2026-10-15 with `research.evaluate` and `research.personal` (5-fold, weight 100); see
"Pruned table for shipping" in [`EXPERIMENTS.md`](EXPERIMENTS.md).
