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

## 2026-10-15 · Personal dictionary through the crate, on chat

Question: does the crate's personal dictionary give the gain `research.personal` measured on chat,
and what does it cost per syllable? Setup: the chat set is rebuilt the way it was first built: the
user's own messages typed into Claude Code on this machine, run through `research.chat_testset`,
kept in RAM and deleted after the run. It now holds the messages written since, so its figures are
not comparable with the earlier chat figures. Both trimmed tables. `research.personal TABLE CHAT 0
100` (weight 0 is the table alone; the total bug of "Personal dictionary in Rust" is fixed), and
`cargo run --release --example personal_eval TABLE LINES` on `research.crosscheck --lines CHAT`:
the same five contiguous folds, the crate learning the other four fifths, and every syllable of the
fold typed into `Typing` with the learned counts and timed.

Prediction: the table alone scores the same in Python and the crate (small 88.3%, large 88.9%).
Python with the personal dictionary: small 92.0%, large 92.3%. The crate learns the words the
tables lack, which Python maps to `<unk>`, so it scores about 0.3 points higher: small 92.3%, large
92.6%. Per syllable with the learned counts: p99 under 2.5 ms (1.6 ms without, wiki).

Result: the chat set has 3,881 sentences, 53,371 words.

| Table | Alone (Python = crate) | Python personal | Crate personal | Crate p99 per syllable |
| --- | --- | --- | --- | --- |
| small | 88.63% | 92.19% | 91.97% | 2.29 ms |
| large | 89.25% | 92.42% | 92.23% | 2.65 ms |

The table alone matched to the word, as predicted, though both figures sit 0.3 above the guess. The
personal dictionary missed in direction: the crate scores 0.2 points below Python, not 0.3 above.
p99 held on the small table and missed on the large one (2.65 ms against 2.5).

Why: comparing each word's guess on the small table, Python alone is right on 206 words, the crate
alone on 87, both wrong but different on 56. The losses cluster on English words that share a
Vietnamese syllable's letters (`the` → `thế`, `on` → `ơn`, `to` → `tổ`, `yet` → `yết`) and on
common syllables next to them (`dùng` → `dụng`, `cài` → `cái`). The likely cause, not yet tested:
Python folds every word the table
lacks into `<unk>`, so a learned context of code and English words pools into one slot that has
both the table's `<unk>` counts and many learned followers. The crate gives each such word its own
id with no table counts, so a context word seen once tells it little and the guess falls back to the
Vietnamese prior. Learning new words does help where it applies (`để` for `de`, `vẫn` for `van`),
but less than pooling helps here. Next: let a learned word the table lacks back off to the table's
`<unk>` counts as a context, and measure again.

## 2026-10-15 · New words as `<unk>` in context

Question: does reading a learned word the table lacks as `<unk>` when it is a context close the 0.2
points the crate lost to `research.personal` on chat ("Personal dictionary through the crate, on
chat")? Change: `Personal` also counts each learned n-gram with such words folded into `<unk>` in
context position (and as the last word of the n-grams that serve as a longer one's context), and
`logp` looks contexts up that way. The new word itself stays a candidate with its own counts.

Check 1, against Python: learn every line of the subs test file, including lines with words the
tables lack (which the earlier cross-check left out), and restore the wiki and forum runs with
`research.personal` and with `cargo run --release --example restore TABLE --learn`. With contexts
pooled the two models agree except where a new word adds a candidate, so: before the change (main)
at least 30 runs differ per set and table; after it, at most 10.

Check 2, chat, rebuilt as before and deleted after: the crate's personal dictionary rises to
Python's or above: small at least 92.2%, large at least 92.4% (Python 92.19% and 92.42%).

Result, check 1 (runs that differ from Python, of 11,765 wiki and 10,179 forum runs):

| Table, set | main | context as `<unk>` | and new words out of the total |
| --- | --- | --- | --- |
| small, wiki | 5 | 0 | 0 |
| small, forum | 3 | 1 | 0 |
| large, wiki | 2 | 0 | 0 |
| large, forum | 8 | 5 | 1 |

The "before" half missed: 2–8 runs, not 30 or more. Subtitles hold few words the tables lack, so the
pooled contexts rarely come into play on wiki and forum text. Pooling alone left 6 runs, 4 of them
with no new word in the crate's output. Their cause was the total: `research.personal` adds learned words
from `uni[3:]`, which leaves `<unk>` out, and the crate counted new words in it. The crate now
leaves them out too. The one run left has three French words from the subtitles, which the crate
offers as candidates and Python cannot: the intended difference.

Result, check 2 (chat, rebuilt: 3,885 sentences, 53,402 words; four more messages than the last
entry, so Python and main are rerun on it):

| Table | Python | crate, main | crate, this change |
| --- | --- | --- | --- |
| small | 92.20% | 91.98% | 92.11% |
| large | 92.43% | 92.24% | 92.37% |

Missed: the change recovers 0.13 of the 0.22 points, not all of them. Per word on the small table,
Python alone is right on 92 words (206 before), the crate alone on 47, both wrong on 29; the English
look-alikes are gone. 162 of the 168 sit within two words of a word the table lacks. The rest of the
gap is the new word as the predicted word: Python scores it as `<unk>` after its context (`gói`
followed by a package name), the crate by its own exact n-grams, which are mostly unseen.

The pooled lookups first cost about half again per syllable (p99 3.2 ms against 2.2 on the small
table); looking in the pooled maps only for keys that hold `<unk>` brings it to 2.3–2.5 ms against
2.2 on main, two runs each, with the same scores.

Next, predicted before the change: a new word whose unmarked form the table does not offer at all
(so it never competes with a table spelling) is scored as `<unk>` after its context, times its share
of the learned spellings of that form; a new word that competes with table spellings keeps its own
counts. Prediction: chat within 0.03 of Python (small at least 92.17%, large at least 92.40%); check
1 drops the last differing run (large forum 1 → 0).

Result: hit. Chat: small 92.20%, large 92.43%, equal to Python to the hundredth. Check 1: 0 runs
differ on all four (large forum 1 → 0). On chat the crate now restores like `research.personal`;
the new words it offers where a table spelling exists gain nothing measurable here.

Time per syllable, small table, three runs each against main on the same machine: p50 0.063–0.068
ms against 0.050–0.056, p99 2.41–2.86 ms against 2.18–2.47; large table p99 2.63 against 2.41.
Precomputing each new word's share when it is learned did not move this. The extra time is the
table's `<unk>` counts, now looked up wherever a new word stands, as `research.personal` does.

## 2026-10-16 · Test sentences that also occur in training text

Question: the fetch scripts hold out whole articles, pages or subtitle lines, but nothing checks the
held-out sentences against the rest of the training text. How many test sentences occur verbatim in
a training corpus, and how much do they raise the reported accuracy? Setup: `python -m
research.overlap OUT` compares each training line whole and split with the fetchers' own sentence
split (`[.!?\n]+`), whitespace collapsed; a test sentence counts if it equals one of these. It
writes `OUT/SET.found` and `OUT/SET.clean`, scored with `python -m research.evaluate TABLE
test/SET OUT/SET.found OUT/SET.clean`. A first version split training lines only at sentence ends
and so could not see subtitle lines, which keep their final punctuation: it found 80 of the subs
test lines instead of 1,295. The independent review that raised this found 1,286 subs test lines
equal to a whole training line, close to the 1,295 here. This is a lower bound: a test sentence
inside a longer training sentence is not counted (the review, counting such spans, found about
twice as many on wiki).

Test sentences found in their own corpus: wiki 469 of 4,000, subs 1,295 of 4,000, web 139, forum
92–195 per forum file. Across corpora: web test in wiki 93, forum-2 test in wiki 56, the rest under
70.

Prediction, small table, `research.evaluate`, each test set split into the sentences found in any
training corpus and the rest: the found ones score 2–4 points higher; leaving them out lowers the
reported word accuracy by about 0.3 on wiki, 1.5 on subs, under 0.3 on web and forum.

Result, small table (word accuracy; whole set, found sentences, the rest):

| Set | Whole | Found | Rest |
| --- | --- | --- | --- |
| wiki | 94.84% | 93.36% (518) | 95.03% |
| subs | 95.11% | 95.01% (1,297) | 95.14% |
| web | 95.00% | 94.04% (171) | 95.02% |
| forum | 91.82% | 96.02% (293) | 91.69% |

Missed: the found sentences are not easier, except on forum. Leaving them out moves the reported
figure by +0.19 (wiki), +0.03 (subs), +0.02 (web) and −0.13 (forum). Likely because the table only
keeps n-grams seen 50 or 20 times, so one copy of a sentence barely moves it. Why the found wiki
sentences are harder than the rest was not looked into.

Prediction for the large table (3-grams seen 5+ times, so a few copies can matter): the difference
stays under 0.5 points on every set.

Result, large table:

| Set | Whole | Found | Rest |
| --- | --- | --- | --- |
| wiki | 96.55% | 96.04% | 96.61% |
| subs | 96.34% | 96.97% | 96.12% |
| web | 96.20% | 95.84% | 96.20% |
| forum | 93.74% | 97.58% | 93.62% |

Hit: leaving the found sentences out moves the figure by +0.06, −0.22, 0.00 and −0.12. So the
reported accuracies are not inflated by more than about a quarter point by verbatim sentences.
Not measured: test sentences that occur only inside a longer training sentence, and near-duplicates
that differ by more than whitespace. The test sets are kept as they are, so earlier figures stay
comparable; a rebuilt, text-disjoint set would start a new series.

The same review raised points that change how results should be read, not the figures:

- The combined forum test set is the first 4,000 lines of forum-1, forum-2 and forum-3 (1,362, 865
  and 1,773); it has none of forum-4.
- The chat set has been used to choose table sizes and settings, so chat figures are validation
  figures, not an independent final estimate.
- "Kneser-Ney against stupid backoff" compares two whole configurations: the Kneser-Ney model drops
  candidate spellings outside its own vocabulary, so the difference is not smoothing alone.
- Word accuracy counts every syllable in a run, including ones with a single spelling (6.8% of wiki
  tokens on the small table); on the ambiguous ones alone wiki is 94.49% instead of 94.84%.
- The personal-dictionary folds split the chat set by position, so a message repeated in the set can
  land in both the learned and the scored part; not measured on chat.
- `research.evaluate` scored only the words a restore returned, so a shortened run would have
  looked right. It now raises instead; the measured runs returned every word, so no figure changes.

## 2026-10-17 · Next-word suggestions from the table

Question: the table already holds which words follow which. If the input method offered the K most
likely next words after each word, how often would the word typed next be among them? Setup:
`python -m research.next_word TABLE test/SET --k 3`. The context is the two words before, as typed
with marks; a run starts after punctuation, as in restore. Suggestions are ranked by the same
stupid-backoff score restore uses and never include sentence markers or `<unk>`. A word the table
does not know is always a miss. A pair counts when one of the three suggested pairs (each suggested
word followed by its best next word) equals the next two words. The corpora and tables were rebuilt
after the RAM disk was cleared, with the commands in the README and `--min-tri 50 --min-bi 20
--min-plain 1000` (small) and `--min-tri 5 --min-bi 3 --min-plain 1000` (large); the rebuild counts
only if the small table scores wiki at 94.84% again with `research.evaluate`.

Prediction, small table: top 1 between 15% and 27%, top 3 between 25% and 42% on wiki, subs and
forum, subs highest. Pair in top 3: 10–18%. Large table: top 3 two to four points higher.

Rebuild check: the rebuilt counts are close to the earlier ones, not identical (vocabulary 577,397
instead of 577,794; 15.29M bigrams and 73.48M trigrams instead of 15.21M and 73.09M; small table
22,650,896 bytes). `research.evaluate` on the small table gives wiki 94.85% (was 94.84%), subs
95.11% and forum 91.82% (unchanged). The figures below are a new series on the rebuilt tables.

Result (share of words; in-vocab is the ceiling, since an unknown word is never suggested):

| Set | In vocab | Top 1 | Top 3 | Pair in top 3 |
| --- | --- | --- | --- | --- |
| wiki, small | 96.81% | 22.32% | 33.94% | 7.92% |
| subs, small | 98.85% | 16.20% | 27.65% | 3.60% |
| forum, small | 98.86% | 17.37% | 27.08% | 4.08% |
| wiki, large | 96.81% | 23.99% | 36.50% | 8.77% |
| subs, large | 98.85% | 17.26% | 29.40% | 3.95% |
| forum, large | 98.86% | 18.93% | 29.65% | 4.77% |

Top 1 and top 3 hit the predicted ranges; subs is not the highest but among the lowest, with wiki
highest. Pairs missed: 3.6–8.8% instead of 10–18%. The large table adds 2.6 (wiki), 1.8 (subs) and
2.6 (forum) points to top 3, so subs missed the predicted two to four. About one word in three is
among three suggestions, and two words in a row rarely are.

The same on the chat set, now kept in the order typed with repeats (earlier chat sets dropped
repeated messages): learn from the first 80% of its sentences (`--learn`, weight 100) and score the
last 20%. The chat messages are written to a coding assistant, not to customers, so they repeat less
than a shop's replies would. `python -m research.repeats test/chat --prefix 2` also counts how often a
scored sentence repeats an earlier one, and how often the earlier sentence offered after its first
two words is the one typed.

Prediction, chat, small table: top 3 between 25% and 35% from the table alone, and 3 to 8 points
higher with the learned part. Under 5% of sentences repeat an earlier one; the offered whole sentence
is right for under 3%.

Result, chat (2,508 sentences from 2,417 messages; 2,006 learned, 502 scored, 5,364 words, 94.09%
in vocabulary):

| Table | Top 1 | Top 3 | Pair in top 3 |
| --- | --- | --- | --- |
| small | 7.77% | 14.45% | 0.97% |
| small + learned | 10.87% | 18.18% | 1.58% |
| large | 8.50% | 15.10% | 1.01% |
| large + learned | 11.39% | 18.59% | 1.68% |

Missed: the table alone puts the next chat word in its top 3 for 14–15% of words, half the 25–35%
predicted and half its rate on the corpora. The learned part adds 3.7 (small) and 3.5 (large) points,
inside the predicted 3–8. `research.personal` learns only words the table knows, while the crate
also learns new ones, so the learned rows may be low. Repeats: 3.78% of the scored sentences repeat
an earlier one; after the first two words an earlier sentence is offered for 44.22% of them and is
the one typed for 2.99% (after three words: 13.56% offered, 1.48% right). Both are under the
predicted 5% and 3%, the second barely.

So on this writing, word suggestions from the table are wrong more than five times in six, and
offering whole earlier sentences would mostly offer the wrong one. Not measured: messages to
customers, which likely repeat more.

## 2026-10-17 · Fixing syllables the table does not know

Question: a typo often makes a string that is no Vietnamese syllable (`khogn`, `phmi`). Can such
syllables be fixed automatically, and at what margin is that safe? Setup: `python -m research.typo
TABLE test/SET`, input typed without marks. Only a syllable whose unmarked form the table does not
know is a target; candidates are the known forms one edit away, ranked in context by the restore
score, and the fix is made when the best beats the runner-up (or keeping the word) by the margin.
The clean pass counts words that would be changed. The mistyped copy has one typo per sentence in a
known syllable of two or more letters: a neighbouring key 40%, two letters swapped 20%, a letter left
out 20%, an extra key 20% (assumed shares, not measured). Typos that land on another known form are
counted and left out; they are the harder case the context spell check covers.

Auto-fixing needs both: clean text changed for at most 0.05% of words, and at least 98% of fixes
right. Prediction, small table: 30–50% of typos land on a known form. At margin 0, 1–2% of clean
words change and 65–80% of scored typos are fixed right; at margin 5, about 0.3% of clean words
change and 95% of fixes are right. No margin meets both limits on chat; on wiki only at margin 6 or
more.

Result, small table (clean words changed / typos fixed right / share of fixes that are right; typos
that landed on a known form are left out of the last two):

| Set | Landed on known | Margin 0 | Margin 4 |
| --- | --- | --- | --- |
| wiki | 41.6% | 0.026% / 66.5% / 94.3% | 0.001% / 41.5% / 99.5% |
| subs | 49.5% | 0.025% / 69.6% / 92.4% | 0.009% / 46.4% / 99.6% |
| forum | 45.1% | 0.025% / 63.0% / 89.2% | 0.007% / 38.8% / 98.6% |
| chat | 47.1% | 0.209% / 44.0% / 86.1% | 0.018% / 19.4% / 98.8% |

Large table, margin 4: wiki 0.008% / 44.0% / 99.4%, subs 0.009% / 47.9% / 99.3%, forum 0.009% /
44.0% / 99.0%, chat 0.021% / 22.0% / 97.9% (margin 5: 0.014% / 17.6% / 99.2%).

The share landing on a known form hit the prediction; the rest missed. Clean text changes far less
than predicted (0.03–0.21% at margin 0, not 1–2%): most unknown words in clean text, such as names
and English words, have no known form one edit away. Fixes are also more often right than predicted.
So both limits are met earlier than predicted: on the small table margin 2 is enough on wiki, and
margin 4 on every set including chat, where it fixes 19.4% of the scored typos and is right 98.8% of
the time. Chat stays the hard case: half the fixes of the corpora at the same margin. Not measured:
real typing, where typos also hit the Telex mark keys, and the share of each kind of typo, which
here is assumed. A personal dictionary would also take the user's own new words out of the targets.
## 2026-10-17 · Fixing unknown syllables on real typos

Question: "Fixing syllables the table does not know" used typos drawn by an assumed model. What does
the fix do with real typos and with the real unknown words of one writer? Setup: the time-ordered
chat messages (2,431, typed with Telex), every syllable whose unmarked form the small table does not
know: 747 forms, 2,506 occurrences. Each form was labelled by hand: a typo of a Vietnamese syllable
with its intended unmarked form, a typo of a foreign word, a typo with no single intended word (two
words run together), unclear (left out), or a real word the table lacks (names, English, product
names, codes). `python -m research.typo TABLE --labels LABELS MESSAGES` scores each occurrence in its
own context; the labels and messages stay on the writer's machine.

The labelling list showed the fix and margin of each form in its first context, so this prediction
is not blind. Prediction, margin 4: under 0.2% of real-word occurrences changed (`sku` → `sau` is one
such case); 3 to 6 of the 15 Vietnamese typos with one intended word fixed right and none fixed wrong; no foreign-word typo
fixed, since their intended words are mostly unknown to the table.

Result (30,700 words in the messages; 2,430 real-word occurrences, 42 foreign-word typos, 17
Vietnamese typos including one with no single intended word, 17 unclear left out):

| Margin | Real words changed | Vietnamese typos fixed right |
| --- | --- | --- |
| 0 | 53 | 7 of 17 (1 wrong) |
| 2 | 8 | 5 |
| 4 | 2 | 3 |
| 6 | 0 | 1 |

Hit, at the low end: at margin 4 two real-word occurrences change (0.08% of them, 1 in 15,000 words
typed; one is `sku` → `sau`, the other was not identified before the messages were deleted), three
Vietnamese typos are fixed right (`nhwung`, `quarn`, `laj` → `nhung`, `quan`, `la`, then marked by
restore) and none wrong, and no foreign-word typo is touched at any margin. Typos that make a
syllable the table does not know are rare in this writing: 17 in 30,700 words, against 2,430 real
words the table lacks. So on this writer the fix is safe but saves little, about one typo per 10,000
words; most of what it would see is real words to leave alone. Several typos missed are Telex keys
left as letters (`aays`, `vieejt`, `ddne`), two edits away from the intended syllable; reading them
as Telex is the input method's job (Cứu chữ). One writer, one labeller.

## 2026-10-17 · A small LSTM for next-word suggestions

Question: the table puts the next word among three suggestions for 27–34% of words on the corpora
and 14–15% on chat. Does a small neural model, trained on this machine's CPU, do clearly better at a
size fit for an input method? Setup: `research.nn_lm`, one LSTM layer (embedding 128, hidden 256)
with an adaptive softmax over the small table's 39,629 words, 7.0M parameters (about 7 MB at one
byte each). It sees the whole line typed so far, not just two words. Training data: 239,664,610
tokens (the build stops when the shortest corpus runs out), lines taken in turn from wiki, subs and
the four forum files (test sentences were already removed by the fetch scripts), 4 hours on 8
threads, which saw 215,449,600 tokens (under one pass), sequences of 64, batch 64, Adam 2e-3.
`python -m research.nn_lm score` counts the same words as `research.next_word` (checked: 2,880 words
on the first 200 forum lines for both), with `<unk>` always a miss. Chat is the last 20% of the
time-ordered set, as before.

Prediction, top 3: wiki 38–42%, subs 32–36%, forum 31–35% (4 to 8 points over the small table),
chat 17–21% (3 to 6 points over the table alone). It counts as clearly better only with at least 5
points over the table alone on chat.

Result (`python -m research.nn_lm score` with the small table's vocabulary; training loss 4.45 at
the end, about 14,900 tokens a second):

| test, top 3 | small table | LSTM |
|---|---|---|
| wiki | 33.94% | 31.70% |
| subs | 27.65% | 26.28% |
| forum | 27.08% | 28.93% |
| chat | 14.62% | 15.66% |

Top 1: wiki 21.50%, subs 15.09%, forum 18.61%, chat 9.45% (table on chat 7.98%). The chat set was
rebuilt from newer messages (2,543 sentences, the last 509 scored, 5,473 words), so the table was
scored again on it: 14.62% instead of the earlier 14.45%. One step plus the top 3 over the vocabulary
takes 1.31 ms (p50) and 1.42 ms (p99) on one thread, measured over 340 steps.

The prediction missed on every set. The LSTM is below the table on wiki and subs, 1.9 points above it
on forum and 1.0 point above it on chat, far from the 5 points that would count as clearly better.
It is fast enough for an input method, so speed is not the limit. Likely causes, not tested: under
one pass over the data is too little for a model that has to learn word pairs the table simply
counts, and 7M parameters are few next to the table's 22.6 MB of counts. Not worth more CPU time in
this form; a larger model would need a GPU, and the gain on chat would have to be shown first.

## 2026-10-17 · Social media comments as a test set

Question: the test sets are edited prose, subtitles, forums and one writer's chat. How does restore
do on many writers' social media comments, abbreviations and all? Setup: `python -m
research.fetch_vilexnorm` writes `test/social` from ViLexNorm at a fixed revision: 9,780 comments
as typed, with at least three words and at least half of them marked. Scored with `python -m
research.evaluate TABLE test/social`; never trained on (CC BY-NC-SA, `docs/DATA_SOURCES.md`).

Prediction: small table 88–91% word accuracy, below forum (91.82%) and close to one writer's chat
without a personal dictionary; large table 1 to 1.5 points higher. Unmarked words changed (the
`plain-changed` column) higher than on forum (8.33%), since abbreviations such as `ko`, `k`, `t`
are common.

Result (`python -m research.evaluate`, forum on the same run for reference):

| table | social | forum |
|---|---|---|
| small | 81.18% | 91.82% |
| large | 83.02% | 93.74% |

Sentences right: 16.34% and 19.78% on social. Plain-changed: 10.95% (small) and 10.11% (large),
against 8.33% and 6.36% on forum.

The prediction missed by 7 to 10 points: social is 10.6 points below forum, not 1 to 4. The large
table adds 1.8 points, a little above the 1 to 1.5 predicted, and plain-changed is higher as
predicted. Where the misses are (small table, a script in the job directory, not committed): 82% are
known marked words given other marks, 14% plain words given marks, 4% typed forms outside the
vocabulary. A neighbour outside the vocabulary does not explain it: words whose neighbours are all
known are right 81.59% of the time (forum 91.82%), and only 4.5% of words have an unknown neighbour.
The most frequent misses are informal and southern forms the corpora rarely write (`lun` restored
as `lùn`, `dị` as `đi`, `tui` as `túi`, `gòi` as `gọi`, `hong` as `hồng`), the writers' own typos
counted as truth (`bới` for `bởi`, `gắp` for `gặp`), and `dc`/`đc`, which writers spell both ways.
So the training corpora do not cover this way of writing; a corpus of informal comments that may be
trained on would be the fix, and this set could then show whether it worked.

## 2026-10-17 · Where the remaining errors are

Question: before trying to raise accuracy, how many errors can no scoring change fix, and how many
words sit in short runs that lack context? Setup: `python -m research.coverage TABLE wiki subs
forum` counts the words whose right spelling is among the candidates restore can pick;
`python -m research.by_length TABLE FILE` splits accuracy by run length (words between two
punctuation marks or digits). Small and large tables (trimmed, N = 1000), the test files frozen
for this series as copies in `test/frozen`.

Prediction: coverage the same for both tables, since they share one vocabulary: wiki 99.0–99.6%,
subs 99.5–99.8%, forum 99.3–99.7%, so under a tenth of the errors are out of reach. Words in runs
of at most four words: wiki 10–20%, subs 25–40%, forum 15–25%, and those runs 3–6 points less
accurate than runs of nine or more. Check that the instrument sees a miss: the unit test scores a
spelling the model never offers as not covered; and accuracy must stay at or below coverage on
every set.

Result: coverage missed high. Both tables cover 99.98% on wiki, 99.97% on subs and 99.95% on forum
(73,604, 31,845 and 92,220 words), so about one error in a hundred is out of reach; the rest are
wrong choices among candidates the table already has. Accuracy stays below coverage on every set.
Short runs (small table, `research.by_length`):

| Set | Words in runs of ≤ 4 | Accuracy, runs ≤ 4 / runs ≥ 9 |
|---|---|---|
| wiki | 17.84% | 92.39% / 95.63% |
| subs | 19.31% | 93.33% / 95.74% |
| forum | 9.18% | 86.86% / 92.78% |

Wiki is inside the predicted share; subs (predicted 25–40%) and forum (15–25%) have fewer short
runs than predicted. The gap is 3.2 points on wiki and 5.9 on forum, as predicted, but 2.4 on subs,
under the predicted 3. Two-word runs on wiki are the worst bucket (89.32%). Keeping context across
commas and digits can reach at most the short runs, about a tenth to a fifth of the words.

## 2026-10-17 · Tuning the backoff weight

Question: stupid backoff multiplies by 0.4 at each step down to a shorter n-gram, the value from
web-scale models; is another value better for these pruned tables? Setup: `python -m
research.evaluate TABLE FILE --backoff X` for X in 0.2, 0.3, 0.4, 0.5, 0.6, 0.8 and 1.0, small
table, on the odd lines of each frozen test file to choose X and the even lines to confirm it.

Prediction: the best X is between 0.3 and 0.6 on every set and gains at most 0.2 points over 0.4
on the even lines; X = 1.0 (no penalty for backing off) is at least 0.5 points worse than 0.4 on
wiki, which shows the instrument sees the setting. If the best X gains under 0.05 on the even lines,
0.4 stays.

Result: missed. Accuracy rises steadily as X falls, and the best value on the odd lines is the
lowest one tried: 0.2 on wiki and forum, 0.3 on subs (95.21% against 95.18% at 0.2). Word accuracy
on the even lines:

| X | wiki / subs / forum |
|---|---|
| 0.2 | 94.99% / 95.14% / 92.03% |
| 0.3 | 94.98% / 95.13% / 91.91% |
| 0.4 | 94.92% / 95.09% / 91.78% |
| 0.6 | 94.74% / 94.90% / 91.45% |
| 1.0 | 94.28% / 94.38% / 90.65% |

X = 1.0 is 0.64 points below 0.4 on wiki, so the setting is seen. X = 0.2 gains 0.07, 0.05 and 0.25
points on the even lines. Since the best value sits at the edge of the range, the sweep goes on
below 0.2 before choosing.

Prediction for 0.05, 0.1 and 0.15, same files: accuracy peaks between 0.1 and 0.2 on the odd lines
and the peak gains at most 0.1 points over 0.2 on the even lines; at 0.05 wiki falls below 0.2.

Result: as predicted. On the odd lines the best X is 0.15 on wiki (94.98%) and subs (95.22%), and
0.1 on forum (92.16%, against 92.12% at 0.15). On the even lines 0.15 gives 94.99%, 95.14% and
92.09%: no change from 0.2 on wiki and subs, +0.06 on forum. At 0.05 wiki falls to 94.92%. Against
0.4, X = 0.15 gains 0.07, 0.05 and 0.31 points on the even lines, at or above the 0.05 threshold on
every set, so the default becomes 0.15, subject to the check on the weighted table below.

## 2026-10-17 · Keeping the n-grams that matter instead of the frequent ones

Question: the small table keeps 3-grams seen 50+ times and 2-grams seen 20+ times, and pruning costs
2.8 points on wiki against the full model (97.61% → 94.84%). Does choosing n-grams by how much they
change scores do better with the same number of n-grams? Setup: `python -m research.prune
wsf-canon.npz OUT --entries 1803455 --min-plain 1000` keeps 1,803,455 bigrams and trigrams in all,
as many as the small table, weighting each by its count times the gap between its own log score
and the backoff score restore would use without it (after Stolcke 1998); a bigram that is the
context of a kept trigram is always kept. Scored with `research.evaluate` on the frozen wiki, subs
and forum files. As a check that the weights matter, the same number of n-grams chosen at random
(`--random 1`).

Prediction, against the small table scored on the same frozen files: file size within 1% of its
22,650,896 bytes. Weighted: wiki +0.3 to +1.0 points, subs and forum +0.1 to +0.8. Random: at least
2 points below the small table on wiki. If the weighted table gains under 0.2 points on wiki, count pruning stays.

Result: as predicted. Both tables are 22,650,896 bytes. Weighted pruning keeps 614,105 bigrams and
1,189,350 trigrams, against 945,625 and 857,830: it trades a third of the bigrams for more trigrams.
Word accuracy on the full frozen files (backoff 0.4):

| Table | wiki / subs / forum |
|---|---|
| small (count pruning) | 94.85% / 95.11% / 91.82% |
| weighted | 95.44% / 95.30% / 92.41% |
| random, same size | 91.73% / 92.17% / 89.09% |

The weighted table gains 0.59, 0.19 and 0.59 points; the random one loses 3.12 on wiki, so the
weights carry the gain. Sentence accuracy on wiki rises from 63.10% to 65.92%.

Prediction for the backoff on the weighted table, odd and even lines as before, X in 0.1, 0.15,
0.2, 0.3 and 0.4: the best X on the odd lines is again between 0.1 and 0.2, and on the even lines
it gains 0.05 to 0.4 points over 0.4.

Result: missed. On the weighted table the curve is flat and the low values lose their edge:

| X | odd lines, wiki / subs / forum | even lines, wiki / subs / forum |
|---|---|---|
| 0.1 | 95.32% / 95.19% / 92.50% | 95.43% / 95.14% / 92.21% |
| 0.15 | 95.35% / 95.25% / 92.52% | 95.46% / 95.22% / 92.25% |
| 0.2 | 95.37% / 95.28% / 92.50% | 95.46% / 95.23% / 92.24% |
| 0.3 | 95.37% / 95.32% / 92.50% | 95.50% / 95.24% / 92.35% |
| 0.4 | 95.37% / 95.32% / 92.47% | 95.50% / 95.27% / 92.35% |

The odd lines pick 0.3 or 0.4 on wiki and subs and 0.15 on forum, where it leads 0.4 by 0.05; on
the even lines 0.4 is best or tied on every set. A low backoff helped the count-pruned table because
it lacked trigrams that the weighted table keeps. The backoff stays 0.4, in Python and in the crate.

Prediction for the personal weight on the weighted table, same chat halves rebuilt, weights 100,
300, 1000 and 3000: the peak is again 1000 on both halves.

Result: missed; the curve is flatter at the top. First half 91.39%, 91.76%, 92.15% and 92.42%;
second half 90.88%, 91.33%, 91.69% and 91.73%. The first half picks 3000, but on the second it gains
only 0.04 over 1000, under the 0.05 used for the backoff, so the weight stays 1000. With weight
1000 the weighted and the count-pruned tables are within 0.04 points of each other on chat.

## 2026-10-17 · Tuning the personal dictionary weight

Question: the personal dictionary adds the user's own counts times 100, a value never tuned; is
another weight better? Setup: the chat set rebuilt in RAM from the same source, split into its
first and second half in time order; `python -m research.personal TABLE HALF 0 10 30 100 300 1000`
(5-fold within each half) on the small table. The first half chooses the weight, the second
confirms it. The chat files are deleted after the run.

Prediction: the best weight is between 30 and 300 on the first half and gains at most 0.3 points
over 100 on the second; 1000 is below 100 on both halves, since the user's few counts then drown
the table. Weight 0 is at least 2 points below 100, which shows the instrument sees the setting.

Result: missed. The rebuilt chat set has 2,556 sentences (1,278 per half, 14,565 and 14,250 words),
fewer than the 3,881 of earlier entries, so its figures do not compare with theirs. Accuracy rises
with the weight all the way to the largest one tried:

| Weight | first half / second half (backoff 0.4) | same at backoff 0.2 |
|---|---|---|
| 0 | 89.63% / 88.95% | 90.05% / 89.17% |
| 100 | 91.43% / 91.08% | 91.69% / 91.08% |
| 1000 | 92.12% / 91.73% | 92.34% / 91.82% |

Weight 0 is 1.8 and 2.1 points below 100 (backoff 0.4). Backoff 0.2 helps here too, by 0.0 to 0.4
points. The chat set keeps repeated messages, so a test sentence can also sit in the training folds,
and a large weight may be rewarded for memorizing it.

Prediction for the follow-up: weights 3000 and 10000 gain under 0.3 points more over 1000; with each
half reduced to its distinct sentences, the best weight falls to 300 or lower and 1000 gains under
0.2 points over 100.

Result: the memorizing guess missed. Only 25 and 20 sentences repeat within a half (1,253 and 1,258
distinct), and the distinct halves give the same curve. Backoff 0.4, small table:

| Weight | all sentences, halves 1 / 2 | distinct sentences, halves 1 / 2 |
|---|---|---|
| 100 | 91.43% / 91.08% | 91.47% / 90.88% |
| 300 | 91.73% / 91.36% | 91.81% / 91.14% |
| 1000 | 92.12% / 91.73% | 92.18% / 91.54% |
| 3000 | 92.04% / 91.68% | 92.12% / 91.54% |
| 10000 | 91.74% / 91.33% | |

The peak is 1000 on both halves, 0.66 to 0.71 points over 100, and accuracy falls beyond it. The
weight becomes 1000. This is one user's text, about 2,500 sentences; a new user's dictionary starts
empty and grows, so the value stays provisional until daily use measures it.

## 2026-10-17 · Weighted pruning at the large table's size

Question: does weighted pruning also help the large table (3-grams ≥ 5, 2-grams ≥ 3, N = 1000,
3,127,619 bigrams and 7,677,041 trigrams)? Setup: `python -m research.prune wsf-canon.npz OUT
--entries 10804660 --min-plain 1000`, scored with `research.evaluate` on the full frozen files next
to the large table, backoff 0.4.

Prediction: the gain is smaller than at the small size, since less is pruned: wiki +0.1 to +0.4
points, subs and forum 0 to +0.3; the file is within 1% of 130,958,840 bytes.

Result: as predicted. The entry count was taken from an older log of the large table; the current
file holds 3,142,120 bigrams and 7,686,997 trigrams (10,829,117), so the weighted table is 24,457
n-grams smaller: 130,665,376 bytes, 0.22% under. It keeps 2,524,178 bigrams and 8,280,484 trigrams.

| Table | wiki / subs / forum |
|---|---|
| large (count pruning) | 96.55% / 96.34% / 93.74% |
| weighted, slightly smaller | 96.87% / 96.46% / 93.84% |

The gain is 0.32, 0.12 and 0.10 points, smaller than at 22 MB (0.59, 0.19 and 0.59).

## 2026-10-17 · The crate with weighted tables and weight 1000

Question: does the crate still restore exactly like Python on a weighted table, alone and with the
personal dictionary at the new weight 1000? Setup as in "Personal dictionary in Rust": `python -m
research.crosscheck` (and `--personal`, learning the frozen subs file) against `cargo run --release
--example restore TABLE [--learn LEARNED]` on the frozen wiki and forum files, small weighted table.
As a check that the comparison sees the weight, the crate's output at 1000 is also compared with
Python's at the old weight 100.

Prediction: 0 differing runs on both sets, alone and with learning; against Python at weight 100,
at least 10 runs differ on each set.

Result: as predicted. Wiki: 11,765 runs, 0 differ alone and 0 with learning (4,904 learned runs),
137 changed by learning, 112 differ from Python at weight 100. Forum: 10,179 runs, 0 and 0, 377
changed by learning, 332 differ from Python at weight 100.

## 2026-10-17 · Backoff that knows how much of a context was pruned

Question: a pruned table still holds each context's full count, so it knows what share of that count
its kept longer n-grams cover. When a context kept almost all its continuations, an unseen one is
truly rare; does charging more for backing off from such contexts help? Setup: `research.leftover`
adds gamma times the log of the unkept share at each step down (gamma 0 is plain stupid backoff);
`python -m research.evaluate TABLE FILES --leftover GAMMA` for gamma 0.1, 0.25, 0.5 and 1 on the
weighted small table, backoff 0.4, odd lines to choose and even lines to confirm. Unit tests check
that gamma 0 gives the plain scores exactly and that the share rises with pruning.

Prediction: the best gamma on the odd lines is 0.25 or 0.5, and on the even lines it gains 0.1 to
0.4 points over gamma 0 (95.50%, 95.27% and 92.35%) on wiki and forum, less on subs; gamma 1 is
below the best. If the gain on the even lines is under 0.05 on every set, the idea is dropped.

Result: as predicted. Word accuracy, weighted small table, backoff 0.4:

| gamma | odd lines, wiki / subs / forum | even lines, wiki / subs / forum |
|---|---|---|
| 0 | 95.37% / 95.32% / 92.47% | 95.50% / 95.27% / 92.35% |
| 0.1 | 95.42% / 95.43% / 92.57% | 95.59% / 95.29% / 92.46% |
| 0.25 | 95.52% / 95.44% / 92.69% | 95.66% / 95.37% / 92.50% |
| 0.5 | 95.63% / 95.52% / 92.76% | 95.68% / 95.25% / 92.61% |
| 1 | 95.50% / 95.36% / 92.40% | 95.48% / 95.00% / 92.34% |

The odd lines pick 0.5 on every set. On the even lines it gains 0.18 on wiki and 0.26 on forum, and
loses 0.02 on subs.

Prediction for three checks before the crate gets it. (1) At gamma 0.5, backoff 0.3, 0.5 and 0.6
stay within 0.05 points of 0.4 on the even lines. (2) The large weighted table gains 0.05 to 0.3 on
wiki and forum at gamma 0.5, full frozen files. (3) On the chat halves with the personal dictionary
at weight 1000, shares taken from the table alone (the user's counts left out, as the crate would
do), gamma 0.5 changes accuracy by -0.1 to +0.3 points.

Result: (1) missed narrowly. At gamma 0.5 on the even lines, backoff 0.3 gives 95.64%, 95.24% and
92.52%; 0.5 gives 95.70%, 95.31% and 92.65%; 0.6 gives 95.70%, 95.31% and 92.66%. Subs moves 0.06,
just past the 0.05 band. These are the confirmation lines, so choosing on them would not be fair;
the backoff stays 0.4. (2) As predicted: the large weighted table goes from 96.87%, 96.46% and
93.84% to 97.03%, 96.48% and 94.10%, +0.16 on wiki and +0.26 on forum. (3) Higher than predicted on
one half. The chat set has grown since the last entry (14,603 and 14,263 words per half). With
personal weight 1000, gamma 0.5 goes from 92.21% to 92.43% on the first half and from 91.50% to
91.83% on the second, +0.22 and +0.33; without the personal dictionary, +0.37 and +0.48.

The crate gets the same rule (gamma 0.5, `LEFTOVER` in `crates/timsen/src/lib.rs`), with the shares
read from the table at load. Prediction for the crosscheck, small weighted table, frozen wiki and
forum, alone and learning the frozen subs file: 0 runs differ between crate and Python; against
Python with gamma 0, at least 50 runs differ on each set, so the check sees the change.

Result: as predicted. Wiki: 11,765 runs, 0 differ alone, 0 with learning (136 changed by learning),
664 differ from Python at gamma 0. Forum: 10,179 runs, 0 and 0 (304 changed by learning), 1,293
differ from Python at gamma 0. The same figures hold after the speed change below.

Prediction for speed (`.claude/skills/measure-latency`, `typing_eval` on the frozen wiki runs, small
and large weighted tables, the crate on `main` against this branch, alternately twice each): each
syllable's p99 rises by at most 10% (one more lookup on the backoff path); opening a table takes
longer by the pass over its n-grams, under 50 ms for the small table and under 300 ms for the large.

Result: missed at first. Computing the context's share for every candidate triple made each
syllable about half again slower (p99 1.61–1.92 ms on `main` against 2.39–3.09 ms, small table).
The share depends only on the two previous words, so the search now computes it once per pair.
Measured again on the same runs, Xeon E5-2696 v4, load average 17–27, release build, 73,604
syllables per run, `main` and this branch alternately:

| Table | p99 per syllable, `main` / branch (two rounds) | Opening the table |
|---|---|---|
| small | 1.83 / 1.85 ms, 1.86 / 1.82 ms | 2.4–2.7 ms / 44–58 ms |
| large | 1.98 / 2.27 ms, 2.14 / 2.65 ms | 2.8–3.0 ms / 220–298 ms |

The small table shows no difference per syllable. The large one is 15–24% slower, beyond the 10%
predicted but under 3 ms. Opening takes the predicted pass over the n-grams; the small table missed
the 50 ms mark on one of the two rounds. The whole-run accuracy in the same runs (95.65% and 97.03%)
matches `research.evaluate`. On the full frozen files the small weighted table now scores 95.65%,
95.38% and 92.68% (wiki, subs, forum), against 94.85%, 95.11% and 91.82% for the count-pruned table
of the last release plan.
