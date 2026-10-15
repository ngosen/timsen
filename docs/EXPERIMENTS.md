# Experiments

One entry per question, newest last. Each entry: question, setup, prediction (written before the run),
result, conclusion. "Words right" is the share of syllables restored exactly after stripping every mark
from held-out text; `hoà`/`hòa` count as the same word.

Test sets (held out by the fetch scripts, 3+ words, at least one mark):

| Name | Source | Sentences | Words |
| --- | --- | --- | --- |
| `wiki` | Wikipedia, articles with id % 1000 == 7 | 4,000 | 73,604 |
| `subs` | OpenSubtitles, lines n % 1000 == 7 | 4,000 | 31,845 |
| `web` | FineWeb-2 file 0, pages n % 1000 == 7 | 4,000 | 87,833 |
| `forum` | FineWeb-2 files 1–4, forum pages n % 1000 == 7 | 4,000 | 92,220 |
| `chat` | The maintainer's own messages (private, never committed) | 3,749 | 51,807 |

`chat` is the set that matters: it is how a user of the input method writes. It was frozen on
2026-10-15; results before that date used earlier, smaller copies and are only compared within an entry.

## 2026-10-14 · Baseline trigram model

Setup: syllable 1/2/3-grams, stupid backoff (0.4), Viterbi over candidates (same unmarked form, seen
5+ times). Trained on Wikipedia (233M words) and OpenSubtitles (34M words).

| Trained on | wiki | subs | chat (3,385 sentences) |
| --- | --- | --- | --- |
| Wikipedia, most frequent spelling, no context | 72.6% | 66.5% | 76.0% |
| Subtitles | 87.4% | 97.5% | 85.3% |
| Wikipedia | 97.7% | 90.8% | 86.1% |
| Wikipedia + subtitles | 97.6% | 97.0% | 87.4% |

- 99.95% of chat words have the right spelling among the candidates; 76% have more than one.
- Pruning to 3-grams ≥ 20, 2-grams ≥ 10 (37 MB at 12 bytes per entry) costs 0.6 points on chat.
- Personal dictionary (counts from the user's other messages, weight 100, 5-fold): 86.1% → 90.4%.

## 2026-10-15 · Context spell check

Question: can the same model flag a marked word whose context prefers another spelling (`gỗ phím`)?
Setup: `research.spellcheck`, pruned model, one injected error per sentence.

Prediction: at ≤ 1% false alarms, catch 70–85% on wiki and 40–55% on chat; chat false alarms 2–3× wiki.

Result (errors drawn by frequency, i.e. realistic):

| Margin | wiki false alarm / caught | chat false alarm / caught |
| --- | --- | --- |
| 3 | 0.89% / 90.3% | 3.10% / 68.6% |
| 5 | 0.40% / 82.6% | 0.92% / 49.6% |
| 6 | 0.24% / 76.0% | 0.58% / 41.4% |

Uniformly drawn errors are much easier (chat, margin 5: 79.7% caught). Chat false alarms are 6–7× wiki
at the same margin, not 2–3×. Of 40 sampled chat alarms, about 3 were real typos; the rest were
technical and chat words the corpus lacks (vá→và, cài→cái, thử→thư, gộp→góp, phím→phim).

Conclusion: usable on edited text; on chat only with a personal dictionary, underline-and-suggest,
never auto-correct.

## 2026-10-15 · Off-the-shelf transformer

Question: does `peterhung/vietnamese-accent-marker-xlm-roberta` beat the trigram model?
Prediction: about 92% on chat, 97% on wiki.

Result: chat 83.3%, subs 84.3%, wiki 86.9%, against 87.4%, 97.0%, 97.6% for the trigram model. It
never produced `đã` from `da` or `điều` from `dieu` (probability 1.0 on "no change"). Whether its tag
file matches the published weights was not verified. Dropped.

## 2026-10-15 · Accuracy by run length and by personal data

Prediction: 1–2 word runs much worse, rising to about 5 words; personal gains flatten after ~10% of
the messages.

| Run length | Words right | Whole run right |
| --- | --- | --- |
| 1 | 92.7% | 92.7% |
| 2 | 85.7% | 76.8% |
| 3–4 | 84.8% | 63.8% |
| 5–8 | 87.4% | 52.0% |
| 9–15 | 87.5% | 31.6% |
| 16+ | 88.5% | 15.9% |

| Personal words used | Chat words right |
| --- | --- |
| 0 | 87.44% |
| ~1,900 | 88.17% |
| ~3,800 | 88.47% |
| ~9,500 | 89.23% |
| ~19,000 | 90.05% |
| ~38,000 | 90.86% |

Both predictions missed: single words are the easiest (common, unambiguous), and the personal curve
keeps rising, about 0.8 points per doubling, with no plateau in sight.

## 2026-10-15 · More corpora: web and forum text

Setup: FineWeb-2 `vie_Latn` (ODC-By). `web`: every 8th row group of file 0, 261M words. `forum`:
discussion-forum pages of files 1–4, 171M words (classified-ad and SEO hosts dropped). Tone placement
normalized before counting. All rows on the frozen chat set.

Prediction: tone normalization +0.2; web → about 89%; forum ≥ web with fewer words; all four ≈ 89.2%.

| Trained on | chat | wiki | subs | web | forum |
| --- | --- | --- | --- | --- | --- |
| Wikipedia + subtitles | 87.74% | 97.64% | 96.99% | 94.71% | – |
| … with tone normalization | 87.76% | 97.64% | 96.99% | 94.71% | – |
| … + web | 88.55% | 97.67% | 96.93% | 96.90% | 94.14% |
| … + forum | **89.13%** | 97.61% | 96.99% | 96.56% | 94.47% |
| … + web + forum | 89.04% | 97.57% | 96.85% | 97.16% | 94.83% |

- Tone normalization changes almost nothing (+0.02): scoring already treats both placements as one.
- Forum text helps chat more than web text with 35% fewer words; adding web on top of forum lowers
  chat slightly. Forum test pages may share quoted posts with training pages of the same thread, so
  the `forum` column may be optimistic; `chat` is unaffected.
- Peak memory: 14 GB (wiki + subs + forum), 27 GB (all four).

## 2026-10-15 · What an input method sees while typing

Question: how accurate is the model when a word must be fixed as it is typed, and how often could it
ask instead of guessing? Setup: `research.typing_sim`, wiki + subs + forum model, frozen chat set.
"Margin" is how far (log score) the chosen spelling must beat every other spelling to be applied
without asking.

Prediction: left context only about 86%; at a middle margin, about 85% of words applied with about
96% of them right, and the right spelling in the top three for about 95% of the rest.

| Margin | Applied | Right when applied | Right in top 3 when asked |
| --- | --- | --- | --- |
| 1 | 94.0% | 92.0% | 84.7% |
| 2 | 87.7% | 93.9% | 88.6% |
| 3 | 82.1% | 95.4% | 90.1% |
| 4 | 75.3% | 96.6% | 91.2% |
| 6 | 61.0% | 98.0% | 93.4% |

Whole run 89.13%; left context only 79.79%.

- Left context only missed the prediction by 6 points: the next word matters more than expected, so
  an input method should keep revising the last few words rather than fix each one as it is typed.
- Margin 3 matches the prediction (82% applied, 95% right); the top-3 share when asked is 90%, not 95%.

## 2026-10-15 · How much does more forum text pay?

Question: FineWeb-2 has about 26 more files of forum pages (roughly 1.1B words). Is fetching them
worth it? Setup: wiki + subs + forum files 1–2 only (about 85M forum words), frozen chat set.

Prediction: about 88.7% (forum gain per doubling about 0.4 points).

| Forum words | chat |
| --- | --- |
| 0 | 87.76% |
| ~85M (files 1–2) | 88.63% |
| 171M (files 1–4) | 89.13% |

The prediction held (88.63%). The last doubling gave 0.50 points. If that rate holds, all 30 files
(about 7.5× the forum text) would add 1–1.5 points, at several times the training memory (14 GB now).

## 2026-10-15 · Kneser-Ney smoothing

Question: does a properly smoothed model beat stupid backoff on the same text? Setup: KenLM `lmplz`
(commit 4cb443e) on wiki + subs + forum, vocabulary capped at the 65,000 most frequent syllables
(98.48% of tokens); 4-gram singletons pruned. `research.kn_model` reads the ARPA file and restores with
a beam of 64. Candidate spellings come from the stupid-backoff model, so both choose among the same
words.

Prediction: 3-gram about 89.6%, 4-gram about 90.0% on chat (stupid backoff: 89.13%).

| Model | chat | wiki | forum | File size |
| --- | --- | --- | --- | --- |
| Stupid backoff, 3-gram | 89.13% | 97.61% | 94.47% | 1.5 GB |
| Kneser-Ney, 3-gram | 89.39% | 97.63% | 94.96% | 1.1 GB |
| Kneser-Ney, 4-gram | 90.09% | 97.88% | 95.21% | 1.6 GB |

- Smoothing alone is worth 0.26 points, less than predicted (0.5); the fourth word is worth another
  0.70. Whole sentences right on chat: 38.2% → 39.3%.
- Both are far too large for an input method. Pruning cost needs measuring before choosing.

## 2026-10-15 · Stupid backoff with 4-grams

Question: the Kneser-Ney 4-gram gain looked like it came mostly from the fourth word. Does stupid backoff
get it too, so KenLM is not needed? Setup: `research.train --order 4`, same corpora, 4-grams seen once
dropped (35.5M kept), exact Viterbi over the last three candidates.

Prediction: about 89.8% on chat, 97.85% on wiki; peak memory about 28 GB.

| Model | chat | wiki | forum |
| --- | --- | --- | --- |
| Stupid backoff, 3-gram | 89.13% | 97.61% | 94.47% |
| Stupid backoff, 4-gram | 89.25% | 97.79% | 94.76% |
| Kneser-Ney, 4-gram | 90.09% | 97.88% | 95.21% |

- Missed by 0.55 points: the fourth word adds only 0.12 with stupid backoff. Splitting the Kneser-Ney gain
  into "smoothing 0.26 + order 0.70" was wrong; the two interact, and a longer context only pays with
  proper smoothing.
- Peak memory 22 GB, model file 2.2 GB. Scoring took 37 minutes for the three sets (exact Viterbi over
  up to 44⁴ states), against a few minutes for the 3-gram.
- Kneser-Ney is the better model at this size. Whether that holds at the 30–40 MB an input method can
  ship is unmeasured, so the shipped table stays a 3-gram stupid-backoff model for now
  ([`PLAN.md`](PLAN.md)); KenLM would only be needed when building the table.

## 2026-10-15 · Unmarked words in chat

Question: would keeping chat abbreviations (`a`, `e`, `ko`) as typed, or expanding them to the full
word, raise chat accuracy? Setup: wiki + subs + forum 3-gram model, frozen chat set, every word that
is unmarked in the reference.

Prediction: abbreviations are 3–5% of chat words; keeping them as typed gains about 0.8 points.

| Word | Typed unmarked | Wrongly marked | Truly marked with the same letters |
| --- | --- | --- | --- |
| a | 395 | 86 | 68 |
| ko | 273 | 4 | 0 |
| ok | 241 | 0 | 0 |
| b | 231 | 0 | 0 |
| j | 179 | 0 | 0 |
| e | 56 | 2 | 7 |

- Missed: these abbreviations are about 2% of chat words and the model already keeps them, because the
  forum text uses them (`ko` 150,000 times, `e` 136,000). Forcing `a` would gain 86 words and lose up
  to 68 (`ạ`, `à`); expanding to `anh` counts as wrong against the reference. Gain about zero.
- 37.6% of chat words are unmarked in the reference; the model wrongly marks 1.46% of all words. The
  largest groups are English and project words (`ui` → `ủi` 45, `kho` → `khó` 43, `sen` → `sến` 20,
  `not` → `nốt` 16, `doc`, `chat`, `ci`), which the personal dictionary is meant to fix, and words the
  writer left unmarked by habit (`dung` → `đúng` 16, `nay` → `này` 12, `de` → `để` 11), where the
  guess is arguably right and the metric is wrong. So 89.13% slightly understates the model.

## 2026-10-15 · Pruned table for shipping

Question: how much does pruning the wiki + subs + forum 3-gram table to a size an input method can ship
cost, alone and with the personal dictionary on top? Setup: `research.evaluate --min-tri N --min-bi N`
on the 1.5 GB model, and `research.personal ... 100 --min-tri N --min-bi N` (5-fold on chat, weight
100). Sizes count vocabulary, 2-gram and 3-gram entries at 12 bytes each; the real file format comes
later.

| 3-grams ≥ | 2-grams ≥ | 3-grams kept | 2-grams kept | Size |
| --- | --- | --- | --- | --- |
| 1 | 1 | 73.1M | 15.2M | 1,066 MB |
| 20 | 10 | 2.19M | 1.83M | 55 MB |
| 30 | 20 | 1.49M | 1.12M | 38 MB |
| 50 | 20 | 0.91M | 1.12M | 31 MB |
| 50 | 50 | 0.91M | 0.58M | 25 MB |

Prediction (chat / wiki / forum, then chat with personal dictionary):

| Size | chat | wiki | forum | chat + personal |
| --- | --- | --- | --- | --- |
| 1,066 MB | 89.13% | 97.61% | 94.47% | 92.1% |
| 55 MB | 88.6% | 97.2% | 93.9% | 91.9% |
| 38 MB | 88.4% | 97.0% | 93.6% | 91.8% |
| 31 MB | 88.2% | 96.8% | 93.4% | 91.7% |
| 25 MB | 87.9% | 96.6% | 93.1% | 91.5% |

The personal dictionary should win back part of the pruning loss, since the user's own 2- and
3-grams are the ones pruning drops first.

Result (5-fold personal dictionary, weight 100, on chat):

| Size | chat | wiki | forum | chat + personal |
| --- | --- | --- | --- | --- |
| 1,066 MB | 89.13% | 97.61% | 94.47% | 91.79% |
| 55 MB | 88.59% | 95.57% | 92.55% | 91.96% |
| 38 MB | 88.43% | 95.10% | 92.13% | 91.87% |
| 31 MB | 88.41% | 94.82% | 91.82% | 91.81% |
| 25 MB | 88.05% | 94.52% | 91.48% | 91.68% |

- Chat alone held the prediction (0.5–1.1 points lost). Wiki and forum missed badly: pruning costs
  2–3 points there, three times the prediction. The 3-grams pruning drops are mostly edited prose.
- With the personal dictionary the size stops mattering on chat: every pruned table is within 0.2
  points of the full one, and 55 MB beats it. The personal gain on the full table is 2.66 points
  (the earlier +3.4 was on an older chat set and model).
- `research.table` files restore exactly like the pruned model they came from (same scores on all
  three sets at 38 and 31 MB). The real files are larger than the estimate, 51.2 MB and 44.2 MB:
  about 20 MB is vocabulary (562,236 words, their unmarked forms and candidate lists), most of it
  unmarked words seen fewer than 20 times (407,371).

### Larger tables

Question: the editing-prose loss is large and a 100–200 MB file is acceptable on a desktop. How much
of it comes back between 55 MB and 1 GB? Sizes below are the real `.timsen` files, measured after
export.

Prediction:

| 3-grams ≥ | 2-grams ≥ | Estimated file | chat | wiki | forum | chat + personal |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | 5 | 108 MB | 88.8% | 96.3% | 93.3% | 91.9% |
| 5 | 3 | 177 MB | 88.9% | 96.8% | 93.7% | 91.9% |
| 3 | 2 | 278 MB | 89.0% | 97.1% | 94.0% | 91.85% |

Result:

| 3-grams ≥ | 2-grams ≥ | File | chat | wiki | forum | chat + personal |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | (npz, 1.5 GB) | 89.13% | 97.61% | 94.47% | 91.79% |
| 3 | 2 | 278 MB | 89.24% | 96.94% | 94.02% | 92.23% |
| 5 | 3 | 177 MB | 89.00% | 96.58% | 93.76% | 92.16% |
| 10 | 5 | 108 MB | 88.90% | 96.06% | 93.21% | 92.06% |
| 20 | 10 | 68 MB | 88.59% | 95.57% | 92.55% | 91.96% |
| 30 | 20 | 51 MB | 88.43% | 95.10% | 92.13% | 91.87% |
| 50 | 20 | 44 MB | 88.41% | 94.82% | 91.82% | 91.81% |
| 50 | 50 | 38 MB | 88.05% | 94.52% | 91.48% | 91.68% |

- Chat and forum held the prediction (within 0.25 points); wiki missed low by 0.2–0.25 points.
- With the personal dictionary every table from 108 MB up beats the unpruned model, and the 278 MB one
  beats it by 0.44 points; the prediction expected them level. Dropping 3-grams seen once or twice
  helps once the user's own counts are added; why is not measured.
- Each step from 38 MB to 278 MB adds about 0.5 points on wiki and forum and 0.1 on chat with the
  personal dictionary. Above 100 MB the gain is mostly on edited prose.

## 2026-10-15 · Trimming the table vocabulary

Question: about 20 MB of each shipped table is vocabulary, mostly unmarked words seen fewer than 20
times (English words, typos). A plain form whose only spelling is itself restores as typed whether or
not it is in the table, so dropping it only loses its n-grams as context. What does that cost?
Setup: `research.table --min-plain N` drops such forms seen fewer than N times; they become `<unk>`.
Scored with `research.evaluate` and `research.personal` (5-fold, weight 100) on the exported files.
`research.personal` maps the user's words to `<unk>` too, which the planned personal dictionary would
not (it learns words the table lacks), so the personal figures are a lower bound.

Prediction:

| Table | N | File | chat | wiki | forum | chat + personal |
| --- | --- | --- | --- | --- | --- | --- |
| 44 MB | 20 | 30 MB | 88.36% | 94.80% | 91.80% | 91.70% |
| 44 MB | 100 | 27 MB | 88.30% | 94.78% | 91.77% | 91.60% |
| 177 MB | 20 | 163 MB | 88.95% | 96.56% | 93.74% | 92.05% |
| 177 MB | 100 | 160 MB | 88.90% | 96.54% | 93.71% | 91.95% |

## 2026-10-15 · Kneser-Ney at the shipped sizes

Question: Kneser-Ney beat stupid backoff by 0.26 points at 1.1 GB (3-grams). Does it still win at the
two shipped sizes? Setup: `research.kn_export` (wiki + subs + forum, vocabulary capped at 65,000),
KenLM `lmplz -o 3 --prune 0 19 49` and `--prune 0 2 4` (the same count thresholds as the 44 MB and
177 MB tables; KenLM applies the 2-gram threshold to adjusted counts, so it keeps a different number of
2-grams, reported below), `research.kn_model eval` with the stupid-backoff candidates. No personal
dictionary: adding user counts to a Kneser-Ney model needs re-estimating it, which `research.personal`
does not do.

Prediction:

| Model | chat | wiki | forum |
| --- | --- | --- | --- |
| Stupid backoff, 44 MB | 88.41% | 94.82% | 91.82% |
| Kneser-Ney, same thresholds | 88.8% | 95.3% | 92.3% |
| Stupid backoff, 177 MB | 89.00% | 96.58% | 93.76% |
| Kneser-Ney, same thresholds | 89.3% | 96.9% | 94.2% |

Result (N = 0 is the untrimmed file; its personal figure differs from the earlier 91.81% by 0.01
because the table also maps the user's rare marked words to `<unk>`):

| Table | N | Vocabulary | File | chat | wiki | forum | chat + personal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 44 MB | 0 | 562,236 | 44.2 MB | 88.41% | 94.82% | 91.82% | 91.82% |
| 44 MB | 20 | 157,318 | 29.5 MB | 88.46% | 94.82% | 91.83% | 91.86% |
| 44 MB | 100 | 69,898 | 25.5 MB | 88.56% | 94.84% | 91.83% | 91.89% |
| 177 MB | 0 | 562,236 | 177.2 MB | 89.00% | 96.58% | 93.76% | 92.16% |
| 177 MB | 20 | 157,318 | 154.5 MB | 89.03% | 96.57% | 93.76% | 92.18% |
| 177 MB | 100 | 69,898 | 143.2 MB | 89.16% | 96.57% | 93.76% | 92.21% |

- The prediction expected a small loss; trimming gains instead, up to 0.15 points on chat, with wiki
  and forum unchanged. Likely reason, not measured: the dropped words now share the `<unk>` n-grams,
  which say more about the context of a rare word than each word's own few counts.
- Files shrink more than predicted: 44 → 25.5 MB and 177 → 143 MB at N = 100.

### Stronger trimming

Prediction: N = 300 and 1000 keep gaining on chat by about 0.05 points each, wiki and forum unchanged;
the small table reaches about 24 and 23 MB.

| Table | N | Vocabulary | File | chat | wiki | forum | chat + personal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 44 MB | 100 | 69,898 | 25.5 MB | 88.56% | 94.84% | 91.83% | 91.89% |
| 44 MB | 300 | 48,628 | 23.8 MB | 88.58% | 94.85% | 91.84% | 91.95% |
| 44 MB | 1000 | 39,682 | 22.6 MB | 88.58% | 94.84% | 91.82% | 92.05% |
| 177 MB | 100 | 69,898 | 143.2 MB | 89.16% | 96.57% | 93.76% | 92.21% |
| 177 MB | 300 | 48,628 | 137.0 MB | 89.20% | 96.57% | 93.76% | 92.26% |
| 177 MB | 1000 | 39,682 | 130.7 MB | 89.18% | 96.55% | 93.74% | 92.32% |

- Chat alone stops gaining after N = 100 (missed: predicted +0.05 per step); wiki and forum move by
  at most 0.03 points, less than 30 words. Sizes held the prediction (23.8 and 22.6 MB).
- With the personal dictionary chat keeps gaining, +0.16 points from N = 100 to 1000 on both tables.
  `research.personal` maps the user's own rare words to `<unk>` as well, so part of this may be the
  shared `<unk>` counts standing in for words the real personal dictionary would learn by name.
- N = 1000 for both shipped tables: 22.6 MB and 130.7 MB, no measured loss anywhere.

Result for "Kneser-Ney at the shipped sizes" (KenLM kept 1.08M 2-grams and 0.87M 3-grams for the
small thresholds, 3.79M and 7.98M for the large; stupid backoff keeps 1.12M/0.91M and 4.70M/8.41M):

| Model | chat | wiki | forum |
| --- | --- | --- | --- |
| Stupid backoff, small, untrimmed | 88.41% | 94.82% | 91.82% |
| Stupid backoff, small, trimmed (N = 1000) | 88.58% | 94.84% | 91.82% |
| Kneser-Ney, small thresholds | 88.59% | 95.18% | 92.28% |
| Stupid backoff, large, untrimmed | 89.00% | 96.58% | 93.76% |
| Stupid backoff, large, trimmed (N = 1000) | 89.18% | 96.55% | 93.74% |
| Kneser-Ney, large thresholds | 89.46% | 96.79% | 94.16% |

- Forum held the prediction; wiki missed low by 0.1 on both; chat missed low by 0.2 on the small
  table and beat it by 0.16 on the large one.
- Against the trimmed tables (whose vocabulary, 39,682 words, is close to the 65,000 cap here),
  Kneser-Ney gains 0.3–0.5 points on edited prose, and on chat nothing on the small table and 0.28 on
  the large one, with slightly fewer n-grams.
- The personal dictionary is worth 3.4 points on chat, ten times that, and stupid backoff takes it by
  adding counts. Kneser-Ney would need either re-estimation on the user's machine or a second model
  mixed in, neither measured. The shipped tables stay stupid backoff; Kneser-Ney is worth revisiting
  only together with a measured way to add personal counts.

The frozen chat set was deleted after these runs. Chat figures from a new set are not comparable
with the ones above; measure a new baseline first.

## 2026-10-15 · Rust restore against the Python model

Question: does the `timsen` crate restore exactly like `research.model` on the shipped tables?
Setup: `research.crosscheck` writes the unmarked runs of each test set and the Python restoration;
`cargo run --release --example restore` restores the same runs; the outputs are compared line by
line. Both tables (small and large, trimmed at N = 1000), test sets wiki, subs, web and forum. As a
check that the comparison can see a difference, the same run with 3-grams switched off in the crate.

Prediction: 0 differing runs on every set and table. With 3-grams off: more than 1,000 differing runs
on wiki with the small table. Floating-point logs could differ in the last bit between numpy and
Rust; if that shows, a handful of runs on near-ties.

Result:

| Table | wiki | subs | web | forum |
| --- | --- | --- | --- | --- |
| Small, differing runs | 0 of 11,765 | 0 of 5,460 | 0 of 10,082 | 0 of 10,179 |
| Large, differing runs | 0 of 11,765 | 0 of 5,460 | 0 of 10,082 | 0 of 10,179 |
| Small, 3-grams off in the crate | 1,260 of 11,765 | | | |

- The prediction held: the crate restores every run exactly like the Python model, and the
  comparison does see a difference when one is made (1,260 runs with 3-grams off).
- Whole-set restore took 10–34 s per set in one thread (about 0.26 ms per word on wiki with the small
  table, 0.32 with the large), on a machine running other jobs at the same time. Not tuned yet.

## 2026-10-15 · Restoring while typing

Question: when the input method asks for the best spelling after every syllable, how many syllables
must follow a word before its guess is as good as the whole-run restoration, how often does a shown
word change, and how long does each syllable take? Setup: `Typing` in the crate (the Viterbi lattice
grows by one step per syllable; an open run has no end-of-run score), `research.crosscheck ... TRUTH`
for the reference, `cargo run --release --example typing_eval TABLE RUNS TRUTH`. Both trimmed
tables; wiki, subs, web, forum. "Fixed after k": the word as shown once k more syllables were typed,
or the final restoration if the run ended first. The chat set is gone, so this has no chat figure.
Timing follows `.claude/skills/measure-latency`; the machine runs other jobs.

Prediction (small table): fixed after 0, 1, 2, 3, 4 on wiki 88.8%, 93.6%, 94.5%, 94.75%, 94.8%
(whole run 94.84%); on forum 86.0%, 90.6%, 91.5%, 91.7%, 91.8% (whole run 91.82%). About 6% of words
change after first shown. Per syllable p50 0.05 ms, p95 0.3 ms, p99 1 ms, max under 10 ms; the
large table about 1.3 times slower. First syllable after opening under 5 ms.

Result (load average 14–18 during the run):

| Table, set | Fixed after 0 | 1 | 2 | 3 | Whole run | Changed after shown |
| --- | --- | --- | --- | --- | --- | --- |
| Small, wiki | 87.35% | 94.12% | 94.80% | 94.84% | 94.84% | 10.80% |
| Small, subs | 87.92% | 94.44% | 95.09% | 95.10% | 95.11% | 10.72% |
| Small, web | 86.63% | 94.25% | 94.97% | 95.00% | 95.00% | 11.68% |
| Small, forum | 83.95% | 91.10% | 91.79% | 91.82% | 91.82% | 13.42% |
| Large, wiki | 89.04% | 95.65% | 96.49% | 96.53% | 96.55% | 10.24% |
| Large, subs | 89.18% | 95.46% | 96.24% | 96.34% | 96.34% | 10.20% |
| Large, web | 88.06% | 95.29% | 96.13% | 96.18% | 96.20% | 11.08% |
| Large, forum | 85.74% | 92.67% | 93.63% | 93.73% | 93.74% | 12.93% |

| Table | p50 | p95 | p99 | Max | Open | First syllable |
| --- | --- | --- | --- | --- | --- | --- |
| Small | 0.14–0.20 ms | 0.88–0.96 ms | 1.55–1.64 ms | 8.2 ms | 2.0–2.7 ms | 0.06–0.20 ms |
| Large | 0.17–0.24 ms | 1.02–1.10 ms | 1.76–1.88 ms | 10.4 ms | 1.9–2.4 ms | 0.08–0.18 ms |

- The whole-run column equals `research.evaluate` on the same tables (wiki 94.84% and 96.55%,
  forum 91.82% and 93.74%), so the harness scores like the Python one.
- Three following syllables give the whole-run accuracy to within 0.02 points on every set; two
  give all but 0.04–0.10. An input method can treat words three syllables back as final. Prediction
  for "after 0" was 1.5 points too high and for "after 1" 0.5 too low: the next word matters even
  more than expected, the ones after it less.
- 10–13% of words change at least once after they are first shown, almost twice the predicted 6%.
  Showing every guess as final would flicker; this is what the confidence of the next step is for.
- Per-syllable time missed the prediction (p50 0.14 ms against 0.05) but stays under 2 ms at p99.
  Each call spells the whole run, so long runs cost more; the 10.4 ms maximum is one such call.

## 2026-10-15 · Confidence and choices while typing

Question: can a per-word confidence tell an input method which guesses to show as settled and which
to offer as a choice, and do the top three choices hold the right word when it is unsure? Setup:
`Typing::choices` scores each spelling of a word by its best path through the run (max-marginals:
the forward scores already kept, met by a backward pass over the last few syllables); confidence is
the best spelling's share of the probability over all spellings. Same runs, tables and command as
"Restoring while typing". Scored at thresholds 0.5, 0.7, 0.9, 0.95 and 0.99, twice: for each word
when it is first shown (the last word of an open run), and for the finished run. "Changed words
flagged": of the words that change after first shown, the share that were below the threshold when
shown.

Prediction (small table, threshold 0.9): when first shown on wiki, 70% of words sure, 97% right when
sure, the truth in the top three for 95% of unsure words, 80% of later-changed words flagged. For
the finished run on wiki 88% sure, 98.5% right when sure, 97% in the top three when unsure; on forum
84% sure and 97.5% right when sure. Choices for the last three words p99 under 1 ms.

Result (load average 5–11 during the run). The accuracy and change columns of "Restoring while
typing" came out identical, so the added calls do not disturb the guesses.

Threshold 0.9, both views:

| Table, set | When shown: sure / right when sure / top 3 / flagged | Finished run: sure / right when sure / top 3 |
| --- | --- | --- |
| Small, wiki | 69.96% / 98.17% / 92.62% / 93.03% | 89.06% / 98.85% / 92.97% |
| Small, subs | 68.49% / 97.92% / 93.78% / 92.71% | 88.29% / 98.76% / 95.28% |
| Small, web | 68.09% / 97.80% / 92.23% / 92.45% | 89.05% / 98.81% / 93.22% |
| Small, forum | 63.16% / 96.87% / 92.14% / 92.36% | 83.41% / 97.90% / 92.79% |
| Large, wiki | 73.35% / 98.40% / 93.86% / 91.56% | 92.78% / 99.14% / 94.03% |
| Large, subs | 71.19% / 98.06% / 94.28% / 90.73% | 91.38% / 98.97% / 96.21% |
| Large, web | 71.15% / 98.01% / 92.61% / 90.97% | 92.03% / 99.02% / 94.36% |
| Large, forum | 67.27% / 97.03% / 92.36% / 90.70% | 88.07% / 98.22% / 93.12% |

Small table, wiki, by threshold:

| Threshold | When shown: sure / right when sure / flagged | Finished run: sure / right when sure |
| --- | --- | --- |
| 0.5 | 92.98% / 90.88% / 36.21% | 98.02% / 95.96% |
| 0.7 | 82.93% / 95.08% / 73.01% | 94.32% / 97.53% |
| 0.9 | 69.96% / 98.17% / 93.03% | 89.06% / 98.85% |
| 0.95 | 62.73% / 99.02% / 97.29% | 86.16% / 99.24% |
| 0.99 | 49.05% / 99.66% / 99.57% | 78.63% / 99.62% |

| Table | Choices for the last three words: p50 | p95 | p99 | Max |
| --- | --- | --- | --- | --- |
| Small | 0.29–0.40 ms | 1.66–1.77 ms | 2.90–2.98 ms | 11.7 ms |
| Large | 0.35–0.48 ms | 1.96–2.04 ms | 3.33–3.48 ms | 13.0 ms |

- Confidence sorts words as hoped. At 0.9 a word shown as sure is right 97–98.4% of the time when
  first shown and 97.9–99.1% in the finished run, against 84–89% and 92–97% for all words.
- It also predicts flicker: 91–93% of the words that later change were below 0.9 when first shown
  (predicted 80%). An input method can underline or grey a word below 0.9 and expect almost every
  later change to land on such a word.
- The share of sure words matched the prediction (wiki 69.96% when shown against 70%; finished
  89.06% against 88%, forum 83.41% against 84%); right-when-sure came out slightly better.
- The top three missed: they hold the truth for 92–96% of unsure words, not 97%, and raising the
  threshold barely helps. Not yet checked why; one guess is words whose right spelling is not among
  the table's candidates at all, which no ranking can fix.
- Choices take about twice a syllable's guess (p99 2.9–3.5 ms against the predicted 1 ms): the
  backward pass over two steps scores every triple of candidates, as a push does, and spells three
  candidates per word. Asking for both after each syllable stays near 5 ms at p99.

## 2026-10-15 · Marked words and two readings

Question: when the user types some words with marks, does keeping them as context help the words
that are guessed? And when the input method passes both readings of a word, as it interpreted the
keys (`tét`) and as the raw letters (`test`), how many words does choosing between them fix, and how
many does it break? Setup: `Typing::push` keeps a marked word as typed and looks it up in either
tone placement; `Typing::push_either` takes both readings. `cargo run --release --example
readings_eval TABLE RUNS TRUTH`, same runs as "Restoring while typing", both tables, all four sets.

- Mixed input: every other word keeps its marks, the rest are typed plain; only the plain words are
  scored, against guessing every word.
- Two readings: each word of the truth is typed in Telex through the Ngó Sen engine (`bamboo-core`
  from `ngosen/bamboo_core`, pinned in `Cargo.toml`). A marked word is typed as its keys, so its raw
  reading is the keys (`tieengs`); an unmarked word is typed as is, so the engine may change it
  (`test` → `tét`). After the run ends, a word takes its raw reading only when that ranks first with
  at least the threshold's confidence; when it ranks first below the threshold it is counted as a
  suggestion. "Fixed": the engine changed the word and the raw reading put it back. "Broken": the
  engine had it right and the raw reading replaced it.

A check on two made-up lines before this entry found that raw keys the table does not know
(`goox quys`) beat the real words (`gỗ quý`) at 0.99 confidence: unknown words share one pooled count
in the table. `push_either` now drops a raw reading the table does not know; a unit test covers it.

Prediction (small table): mixed input on wiki, plain words 94.8% when all are guessed and 96.5%
next to marked words; on forum 91.8% and 94.0%. The keys of a marked word give it back in all but
0.1% of words. The engine changes about 1% of the words on wiki and 1.5% on forum, 60% of those
known to the table. At threshold 0.9, half of the changed words that the table knows are fixed, and
broken words are fewer than a tenth of the fixed ones. The large table fixes more, since it knows
more unmarked words.

Result. The first run counted 594 marked wiki words whose keys did not give them back, against the
predicted 0.1%: the engine placed tones the old way (`hòa`) while the test sets use the new one. The
harness now sets the engine to the new placement; the counts below are from the second run. Fixed
and broken counts were the same in both runs.

Mixed input, plain words right:

| Table, set | Every word guessed | Next to marked words |
| --- | --- | --- |
| Small, wiki | 94.95% | 95.96% |
| Small, subs | 95.66% | 96.50% |
| Small, web | 95.34% | 96.28% |
| Small, forum | 92.13% | 93.53% |
| Large, wiki | 96.69% | 97.43% |
| Large, subs | 96.68% | 97.34% |
| Large, web | 96.47% | 97.18% |
| Large, forum | 94.07% | 95.17% |

Two readings (the engine and the readings do not depend on the table):

| Set | Words | Changed by the engine (known to the table) | With a known raw reading | Keys do not give back |
| --- | --- | --- | --- | --- |
| wiki | 73,604 | 357 (223) | 4,117 | 146 |
| subs | 31,845 | 80 (54) | 3,967 | 24 |
| web | 87,833 | 146 (98) | 5,321 | 86 |
| forum | 92,220 | 204 (141) | 6,005 | 125 |

Fixed / broken / suggestions right / suggestions wrong:

| Table, set | Threshold 0.5 | 0.9 | 0.99 | 0.999 |
| --- | --- | --- | --- | --- |
| Small, wiki | 161 / 7 / 0 / 0 | 157 / 1 / 4 / 6 | 138 / 0 / 23 / 7 | 101 / 0 / 60 / 7 |
| Small, subs | 26 / 2 / 0 / 0 | 25 / 0 / 1 / 2 | 21 / 0 / 5 / 2 | 18 / 0 / 8 / 2 |
| Small, web | 71 / 4 / 0 / 0 | 51 / 1 / 20 / 3 | 36 / 0 / 35 / 4 | 29 / 0 / 42 / 4 |
| Small, forum | 109 / 4 / 0 / 0 | 87 / 1 / 22 / 3 | 73 / 0 / 36 / 4 | 57 / 0 / 52 / 4 |
| Large, wiki | 175 / 6 / 0 / 0 | 169 / 2 / 6 / 4 | 153 / 0 / 22 / 6 | 118 / 0 / 57 / 6 |
| Large, subs | 35 / 3 / 0 / 0 | 29 / 0 / 6 / 3 | 27 / 0 / 8 / 3 | 24 / 0 / 11 / 3 |
| Large, web | 78 / 6 / 0 / 0 | 65 / 1 / 13 / 5 | 44 / 0 / 34 / 6 | 31 / 0 / 47 / 6 |
| Large, forum | 112 / 4 / 0 / 0 | 101 / 1 / 11 / 3 | 84 / 0 / 28 / 4 | 73 / 0 / 39 / 4 |

- Marked words help their neighbours by 0.66–1.40 points, less than the predicted 1.7–2.2.
- The engine changes far fewer words than predicted: 0.5% on wiki and 0.2% on forum, not 1% and
  1.5%. Most are English or French words (`of` → `ò`, `post` → `pót`, `boot` → `bôt`, `core` →
  `coẻ`, `test` → `tét`); 62–69% are known to the table, as predicted.
- At 0.9 the small table fixes 70% of the changed words the table knows on wiki and 62% on forum
  (predicted half), and breaks one word per set at most (`lé` → `les`, `bõ` → `box` on forum). At
  0.99 nothing breaks on any set and 68–93% of the 0.9 fixes remain; the rest become suggestions.
  Switching only at 0.99 and suggesting below it is the setting to try first.
- Words the engine changes that the table does not know stay changed: `messenger` → `mesenger`
  (a doubled `s` undoes a tone in Telex) is the most common on forum.
- The large table fixes 8–27% more words, as predicted, though both tables keep the same unmarked
  words; more 3-grams around them are the likely reason, not checked.
- 146 marked wiki words (0.2%) cannot be typed back, mostly foreign names with accents Telex does
  not have (`Suárez`, `château`); those are left out of the fixed and broken counts.

## 2026-10-15 · Personal dictionary in Rust

Question: does the crate's personal dictionary restore exactly like `research.personal` on the shipped
tables? Setup: `Personal` in the crate learns runs known to be right and adds them, weight 100, on
top of a table; words the table lacks get new ids. `python -m research.crosscheck --personal TABLE
TEXT RUNS LEARNED EXPECTED` learns the lines of TEXT whose words the table knows (a word the table
lacks is `<unk>` in Python but a new word in the crate, so such lines are left out) and restores
RUNS; `cargo run --release --example restore TABLE --learn LEARNED < RUNS` does the same in the
crate. The learned text is the subs test file (public subtitles, used here only as stand-in text);
the runs are the wiki and forum test sets. Both trimmed tables.

Before this check `research.personal` had a bug: on a table file it recomputed the total from the
words the file keeps, so learning anything dropped the counts of the words the table leaves out
(on the test table, 76 became 50 instead of 82). It now adds the learned counts to the table's
total. The chat figures with personal counts in "Trimming the table vocabulary" (92.05% and 92.32%)
were measured with the bug and are not rerun: the chat set is gone.

Prediction: the crate and Python agree on every run of both sets with both tables. Learning the subs
text changes about 3% of the wiki runs and 4% of the forum runs against the table alone, so the check
can see a difference.

Result (4,904 learned runs: the subs lines whose words both tables know):

| Table, set | Runs | Crate and Python differ | Changed by learning |
| --- | --- | --- | --- |
| Small, wiki | 11,765 | 0 | 27 |
| Small, forum | 10,179 | 0 | 55 |
| Large, wiki | 11,765 | 0 | 12 |
| Large, forum | 10,179 | 0 | 51 |

- The crate restores every run exactly like `research.personal`, with both tables.
- Learning changed far fewer runs than predicted (0.1–0.5%, not 3–4%): subtitles are general text
  the tables already hold, not one writer's habits. The changed runs are still enough to show the
  check compares learned counts, not the table alone.
