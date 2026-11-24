# Choosing a table

Tim Sen has two tables in the same file format, used with the same personal dictionary. **The small
table is the default**, and the one the first release ships; the large one is an option for people
who mostly write long edited text.

| | Small (default) | Large |
| --- | --- | --- |
| File | 12.37 MB | 49.69 MB |
| Chat + personal | 89.24% | 88.49% |
| Chat | 82.94% | 83.95% |
| Wikipedia | 96.03% | 97.04% |
| Subtitles | 95.75% | 96.55% |
| Forum | 93.26% | 94.26% |

On edited prose, and on chat before the personal dictionary has learned anything, the large table
gets about one more word in 100 right. Once it has learned, the small table is ahead on chat. Keeping every n-gram of the
model would add 0.5 points on Wikipedia, 0.3 on subtitles and nothing on forum text ("Where accuracy
stops rising, and what fits under 50 MB" in [`EXPERIMENTS.md`](EXPERIMENTS.md)), so the large table
is close to what this model can do.

Both are built from the model trained on Wikipedia, subtitles, forum pages from FineWeb-2 files 1
to 4 and technology forums from files 1 to 29 (`python -m research.train MODEL.npz wiki subs forum
tech`), in format version 3:

```
python -m research.prune MODEL.npz small.timsen --entries 2965860 --min-plain 1000
python -m research.prune MODEL.npz large.timsen --bytes 50000000 --min-plain 1000
```

The figures are from "Format version 3: one byte per count, under 50 MB" in
[`EXPERIMENTS.md`](EXPERIMENTS.md), on the frozen test files. The small table keeps the n-grams of
the 22.65 MB table of format version 2; the large one replaces the 130.96 MB table, which scored
97.15%, 96.59% and 94.30%.

Chat is 18,553 sentences from one writer's Messenger messages ("The two version 3 tables on
Messenger chat"), so it may differ for other people. It is a different set from the 2,604 prompts
to a coding assistant used in version 2, where the small table scored 90.61% and 92.91% with the
personal dictionary and the 130.96 MB table 90.65% and 92.78% ("Forum pages from every FineWeb-2
file"); figures on the two sets are not comparable. How each step got here, from the count-pruned tables of 2026-10-15: choosing n-grams by weight ("Keeping the n-grams that matter instead of the frequent ones"), the
leftover backoff ("Backoff that knows how much of a context was pruned"), the personal weight, now
min(3000, table total / tokens learned) ("A personal weight that falls as the dictionary grows"), the denser format ("A denser table file") and the
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

The whole file is read into memory when it opens, so its size is also the memory it takes: the small
table opens in about 17 ms and holds 19 MB once typing has touched it, the large one in about 44 ms
and 56 MB ("Format version 3: one byte per count, under 50 MB").

Measured on 2026-10-15 with `research.evaluate` and `research.personal` (5-fold, weight 100); see
"Pruned table for shipping" in [`EXPERIMENTS.md`](EXPERIMENTS.md).
