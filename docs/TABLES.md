# Choosing a table

Tim Sen has two tables of word counts in the same file format, used with the same personal
dictionary. The small one ships first; the large one may follow.

| | Small | Large |
| --- | --- | --- |
| File | 22.6 MB | 130.7 MB |
| Chat + personal | 92.19% | 92.42% |
| Chat | 88.63% | 89.25% |
| Wikipedia | 94.84% | 96.55% |
| Forum | 91.82% | 93.74% |

Chat figures are from the rebuilt chat set (3,881 sentences) in "Personal dictionary in Rust",
measured after a bug in the personal counts was fixed; wiki and forum from "Trimming the table
vocabulary".

The figures above are for tables pruned by count. Built with `research.prune` instead, which keeps
the n-grams whose removal would change scores most, the same sizes give wiki 95.44% and 96.87% and
forum 92.41% and 93.84% ("Keeping the n-grams that matter instead of the frequent ones" and
"Weighted pruning at the large table's size"). Backing off costs more from contexts the table kept
nearly whole: then wiki 95.65% and 97.03%, forum 92.68% and 94.10% ("Backoff that knows how much
of a context was pruned"). Version 2 of the file format fits 65% more n-grams in the same bytes;
built with `research.prune --bytes`, the small table gives wiki 96.08%, subs 95.75% and forum
93.25%, and the large one 97.21%, 96.60% and 94.23% ("A denser table file"). Chat on these tables
is not yet measured on the set above. The personal dictionary now weighs a learned n-gram 1000 times one from the corpora,
up from 100 ("Tuning the personal dictionary weight").

They differ in how many rare word sequences they keep. Both leave out unmarked words seen fewer than
1,000 times whose only spelling is themselves (English words, typos); those are restored as typed
either way, and leaving them out cost nothing measurable ("Trimming the table vocabulary" in
[`EXPERIMENTS.md`](EXPERIMENTS.md)).

The table below compares the pruning levels measured to choose them, before that trimming, so the
sizes are larger than the shipped files; the two chosen levels are in bold.

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
it gets about 1.7 more words in 100 right.

The file is mapped from disk, so only the parts in use are read into memory; the size mainly affects
the download.

Measured on 2026-10-15 with `research.evaluate` and `research.personal` (5-fold, weight 100); see
"Pruned table for shipping" in [`EXPERIMENTS.md`](EXPERIMENTS.md).
