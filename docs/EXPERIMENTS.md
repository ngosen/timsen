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

## 2026-10-17 · Keeping context across commas and digits

Question: every comma, digit or symbol starts a new run, so the word after it is guessed with no
context; runs of at most four words are 9–19% of words and 2.4–5.9 points less accurate ("Where
the remaining errors are"). Does keeping the run going, with the separator as one `<p>` word, help?
Only `.`, `!` and `?` still end a run. Setup: `python -m research.train --breaks wsfb.npz wiki subs
forum`, the same corpora as `wsf-canon.npz`; a weighted table at the small size (`research.prune
--entries 1803455 --min-plain 1000`); `research.evaluate --breaks` on the full frozen files, which
skips `<p>` when scoring, against the current small weighted table without `--breaks` (95.65%,
95.38% and 92.68%), both with the leftover backoff. Also the two unpruned models. The word counts
must be the same both ways (73,604, 31,845 and 92,220), and `<p>` must be among the most frequent
words of the new model, which shows the change was applied.

Prediction: at the small size, +0.1 to +0.4 points on each set; unpruned, a larger gain, +0.2 to
+0.6, since the `<p>` n-grams do not compete for the budget there. If the small table gains under
0.1 on every set, runs stay as they are.

Result: mostly missed. Training saw 474,954,566 tokens, and `<p>` is the second most frequent word
(37,153,562). Word counts match both ways. Word accuracy, full frozen files, leftover backoff:

| Model | wiki / subs / forum |
|---|---|
| small weighted, runs end at commas | 95.65% / 95.38% / 92.68% |
| small weighted, `--breaks` (22,650,928 bytes) | 95.68% / 95.51% / 92.69% |
| unpruned, runs end at commas | 97.54% / 96.89% / 94.26% |
| unpruned, `--breaks` | 97.70% / 97.12% / 94.41% |

At the small size only subs gains more than 0.1 (+0.13); wiki gains 0.03 and forum 0.01. Unpruned,
the gain is 0.16, 0.23 and 0.15, at the low end of or under the predicted range. The pruned table
spends its budget on `<p>` n-grams (it keeps 591,106 bigrams, against 614,105).

Prediction for the large size (`--entries 10804660`, against the large weighted table's 97.03%,
96.48% and 94.10%): +0.1 to +0.2 on each set.

Result: as predicted. The large `--breaks` table (2,367,864 bigrams and 8,436,796 trigrams) scores
97.17%, 96.61% and 94.28%, +0.14, +0.13 and +0.18.

A table trained with `--breaks` also needs the input method to send `<p>` where the user typed a
comma or digit. Scored on runs that end at commas instead, as an input method that does not would
give it, the small `--breaks` table falls to 95.11%, 95.39% and 92.39%, below the current table on
wiki (-0.54) and forum (-0.29).

Conclusion: the shipped tables keep runs that end at commas. At the small size the gain is 0.01 to
0.13 points, and it turns into a loss if the input method does not mark the separators. `--breaks`
stays in `research.train` and `research.evaluate`; worth taking up for the large table once the
input method passes what was typed before a comma (step 7).

## 2026-10-17 · A denser table file

Question: each bigram and trigram takes 12 bytes, a 64-bit key and a 32-bit count, although a table
holds under 65,536 words. Version 2 of the format groups bigrams by first word and trigrams by the
bigram of their first two words, and stores only the last word's id in 16 bits, with the counts
unchanged: 6 bytes per n-gram plus 4 per bigram for the start of its trigrams. How much more fits
in the same file, and what does it buy? Setup: `research.prune --entries 1803455` as before (the same
n-grams as the small weighted table) and `research.prune --bytes 22650896` and `--bytes 130958840`
(the sizes of the current small and large tables), scored with `research.evaluate` on the full
frozen files; `research.crosscheck` against the crate; `typing_eval` timing as before.

Prediction: the same n-grams take about 13.5 MB and restore exactly as before (95.65%, 95.38% and
92.68%), which shows the format loses nothing. At 22,650,896 bytes the table holds 60–70% more
n-grams and gains +0.2 to +0.4 on wiki and forum and +0.05 to +0.2 on subs; at the large size
+0.1 to +0.3 on wiki. The crate restores exactly like Python, and p99 per syllable stays within
10% of the version 1 file.

Result: the format loses nothing, and the gains beat the prediction at the small size. The same
1,803,455 n-grams take 14,445,128 bytes (36% less, more than the predicted 13.5 MB) and score
95.65%, 95.38% and 92.68%, exactly as the version 1 file.

| Table | n-grams (bigrams + trigrams) | wiki / subs / forum |
|---|---|---|
| small, version 1 | 614,105 + 1,189,350 | 95.65% / 95.38% / 92.68% |
| small, version 2, 22,650,864 bytes | 905,834 + 2,070,759 | 96.08% / 95.75% / 93.25% |
| large, version 1 | 2,524,178 + 8,280,484 | 97.03% / 96.48% / 94.10% |
| large, version 2, 130,958,816 bytes | 4,164,603 + 14,690,801 | 97.21% / 96.60% / 94.23% |

At the small size the table holds 65% more n-grams and gains 0.43, 0.37 and 0.57 points, above the
predicted ranges on every set. The large table gains 0.18, 0.12 and 0.13.

The crate restores the small version 2 table exactly like Python: 0 of 11,765 wiki runs and 0 of
10,179 forum runs differ, alone and after learning the subs file (103 and 290 runs changed by
learning). Speed, `typing_eval` on the frozen wiki runs, Xeon E5-2696 v4, load average about 3,
release build, 73,604 syllables, `main` with version 1 files and this branch with version 2 files,
alternately twice:

| Table | p99 per syllable, two rounds | Opening |
|---|---|---|
| small, version 1 | 1.51, 1.50 ms | 54–56 ms |
| same n-grams, version 2 | 0.56, 0.58 ms | 15–16 ms |
| small, version 2 | 0.63, 0.63 ms | 20–21 ms |
| large, version 1 | 1.77, 1.75 ms | 234 ms |
| large, version 2 | 0.93, 0.93 ms | 87–108 ms |

Restore got faster instead of staying level: a lookup now searches one word's or one context's
short list of 16-bit ids instead of the whole sorted key array.

## 2026-10-17 · The version 2 tables on chat

Question: what do the two version 2 tables give on chat, alone and with the personal dictionary, for
`docs/TABLES.md`? Setup: the chat set rebuilt in RAM and deleted after; `python -m research.personal
TABLE CHAT 0 1000` (5-fold over the whole set; weight 0 is the table alone), both tables. The set has
grown since "Personal dictionary in Rust", so its figures do not compare with the 3,881-sentence ones.

Prediction: the large table leads the small one by under 0.5 points with the personal dictionary and
by 0.3 to 1 point alone; the personal dictionary adds 2 to 3.5 points to each.

Result: missed; the small table is ahead on chat. The set has 2,583 sentences, 29,092 words. Alone:
small 89.96%, large 89.86%. With the personal dictionary: small 92.58%, large 92.21%. The personal
dictionary adds 2.62 and 2.35 points. Why is not measured; one guess is that the large table's
extra n-grams come from edited prose, which chat does not resemble.

## 2026-10-17 · A technology-forum slice

Question: the largest error groups on chat are English and project words inside Vietnamese text.
Does adding pages from Vietnamese technology forums and developer Q&A (tinhte.vn, voz.vn,
daynhauhoc.com, viblo.asia, kipalog.com) help? Setup: `python -m research.fetch_fineweb tech FILE`
for FineWeb-2 files 5 to 29, all those the forum corpus (files 1 to 4) does not use, keeping pages
with at least 50% marked words instead of 60%, since English words carry no marks; `research.train
MODEL wiki subs forum tech`; small tables at 22,650,896 bytes (`research.prune --bytes`) from this model and from
the current one, scored on the frozen wiki, subs and forum files, the social set and chat (rebuilt
in RAM, `research.personal` 5-fold, weights 0 and 1000, deleted after). As a check that the slice
holds what it is meant to, the share of words made of ASCII letters only, in the tech data against
the forum data.

Prediction: the tech data has at least twice the forum data's share of ASCII-only words. Chat alone
+0.3 to +1.0 points, chat with the personal dictionary +0.1 to +0.3; wiki, subs and forum within 0.1
of the current small table; social 0 to +0.5.

Result: the gains are as predicted or a little above; the check on the slice missed. Files 5 to 29
give 50,756 pages, 30,469,666 words, mostly tinhte.vn and voz.vn, then viblo.asia; the model now
sees 468,270,670 tokens and keeps 591,048 words. ASCII-only words are 21.10% of the tech data
against 16.16% of forum-1, 1.3 times, not the predicted 2: unmarked Vietnamese syllables (`anh`,
`em`, `ban`) count as ASCII too, so the measure is coarse. The small table (22,650,864 bytes, both)
keeps 40,736 words instead of 39,629.

| Set | small, current | small, with tech |
|---|---|---|
| wiki | 96.08% | 96.05% |
| subs | 95.75% | 95.73% |
| forum | 93.25% | 93.25% |
| social | 82.56% | 83.11% |
| chat alone | 89.92% | 90.53% |
| chat + personal (1000) | 92.59% | 92.90% |

The chat set has 2,595 sentences, 29,249 words, rebuilt in RAM and deleted after the run. Chat
gains 0.61 alone and 0.31 with the personal dictionary, social 0.55; edited prose moves by at most
0.03. The tables are built with the tech slice from now on.

Prediction for the large table with the tech slice (`--bytes 130958840`, against 97.21%, 96.60%,
94.23% and the large table's chat figures in the same run): wiki, subs and forum within 0.1; chat
alone +0.2 to +0.6.

Result: edited prose as predicted, chat above the range, so the prediction missed on the high side.
The large table with the tech slice is 130,958,808 bytes, 4,209,188 bigrams and 14,610,839 trigrams.

| Set | large, current | large, with tech |
|---|---|---|
| wiki | 97.21% | 97.15% |
| subs | 96.60% | 96.58% |
| forum | 94.23% | 94.31% |
| social | 83.42% | 84.20% |
| chat alone | 89.84% | 90.65% |
| chat + personal (1000) | 92.23% | 92.76% |

Same chat set as the small-table run. Chat gains 0.81 alone and 0.53 with the personal dictionary,
more than in the small table; why is not measured, one guess is that the small table has less room
for the tech n-grams.

## 2026-10-17 · Forum pages from every FineWeb-2 file

Question: the forum corpus reads FineWeb-2 files 1 to 4. Do forum pages from files 5 to 29 help
chat, and do they cost edited prose? Setup: technology hosts now leave the forum corpus
(`forum_host` drops `TECH_HOSTS`), so a page is counted once; `research.fetch_fineweb forum` for
files 1 to 29 and `tech` for files 1 to 4 (files 5 to 29 as before; file 0 stays out, it holds the
`web` test set); `research.train MODEL wiki subs forum tech`; small and large tables at the same
byte sizes, scored against the tables from "A technology-forum slice" on the frozen wiki, subs and
forum files, the social set and chat (rebuilt in RAM, `research.personal` 5-fold, weights 0 and
1000, deleted after). As a check that the change took, the forum word count and the model's token
count and vocabulary against that entry's.

Prediction: forum words at least 5 times the current, about 168 million; tokens and vocabulary
both up. Small table: chat alone and chat with the personal dictionary 0 to +0.3; forum +0.1 to +0.5; wiki
and subs -0.2 to 0; social 0 to +0.5. Large table: chat alone 0 to +0.4, forum +0.2 to +0.6, wiki
and subs -0.2 to 0.

Setup change before any table was scored: the model has 1,343,270,620 tokens and 783,052 words, and
its table vocabulary is 97,236 words, more than the 65,536 a table holds; 75,982 of them are marked
spellings, against 28,418 in the tech-slice model. Both thresholds are scaled with the token count
(2.87 times): `research.prune --min-candidate 15 --min-plain 3000` instead of the defaults 5 and
1000. The prediction above stands.

Result: missed. Forum words are about 1.04 billion, 6 times as before, and the check passed; the
scores did not move as predicted. Same run, chat set of 2,604 sentences:

| Set | small, tech slice → all forums | large, tech slice → all forums |
|---|---|---|
| wiki | 96.05% → 95.10% | 97.15% → 96.61% |
| subs | 95.73% → 95.41% | 96.58% → 96.32% |
| forum | 93.25% → 93.21% | 94.31% → 94.88% |
| social | 83.11% → 83.97% | 84.20% → 85.67% |
| chat alone | 90.56% → 90.19% | 90.67% → 90.78% |
| chat + personal (1000) | 92.90% → 92.49% | 92.74% → 92.73% |

Forum text is now three quarters of the tokens, and wiki loses up to 0.95 while chat does not gain:
chat resembles the technology slice more than general forums. The raised thresholds are a second
change in the same run and are not separated from the data. The extra forum files are not used.

Prediction for the tables rebuilt with the new filter (forum files 1 to 4 without the technology
hosts, tech files 1 to 29, default thresholds), against the tech-slice tables: every set within 0.1.

Result: as predicted; every set within 0.05. The model has 470,558,538 tokens and 592,158 words,
the tables keep 40,801 words. Same run as above:

| Set | small, tech slice → rebuilt | large, tech slice → rebuilt |
|---|---|---|
| wiki | 96.05% → 96.03% | 97.15% → 97.15% |
| subs | 95.73% → 95.73% | 96.58% → 96.59% |
| forum | 93.25% → 93.26% | 94.31% → 94.30% |
| social | 83.11% → 83.13% | 84.20% → 84.23% |
| chat alone | 90.56% → 90.61% | 90.67% → 90.65% |
| chat + personal (1000) | 92.90% → 92.91% | 92.74% → 92.78% |

These rebuilt tables are the ones `docs/TABLES.md` describes from now on.

## 2026-10-19 · A personal dictionary from years of messages

Question: the user's own Messenger messages are now available, about 2.2 million words from 2011 to
2026. How much does a personal dictionary learned from them help, and do old messages, written when
habits were different, still help or start to hurt? Setup: the user's own messages only, kept when
they have at least 3 words and at least 60% marked words (1.63 million words before the test year);
held in RAM and deleted after the run. The test is the last year of messages (4,918 messages,
33,973 words); the dictionary learns from the 1, 3 or 5 years before it (64,133, 366,370 and 766,954
words) or from everything before it (1,626,109 words). `research.personal TABLE TEST 0 100 300 1000
--learn FILE`, small table. As a check that the windows differ, the word counts above; weight 0 must
score the same for every window.

Prediction: weight 0 89 to 92%. One year at weight 1000: +2 to +4 points. Three years against one,
best weight for each: +0.3 to +1.0. Five against three: -0.2 to +0.3. Everything against five years:
-0.3 to +0.2, so old messages neither help nor hurt much. The best weight falls as the dictionary
grows: with everything, 100 or 300 beats 1000.

Second test, written before the first one's numbers were read: the user's own Facebook posts (on
their profile and on other pages; comments are not in the export), same filter, all years: 2,697
posts, 113,072 words. The dictionary learns from all messages before the message test year
(`--learn` with the everything window), at weights 0, 100, 300 and 1000. Posts are text written for
others to read, closer to web and social content than messages.

Prediction: weight 0 90 to 94%, above chat since posts are longer and more edited; the dictionary
learned from messages +1 to +3 points at its best weight, less than on messages, since posts are a
different register.

Result, messages: the base missed low and every gain missed high; old messages help. Weight 0 scores
83.90% for every window, as it must (33,387 words: the 33,973 above count whitespace-separated tokens, including numbers and symbols).

| Learned from | Weight 100 / 300 / 1000 |
|---|---|
| nothing | 83.90% |
| 1 year | 87.33% / 88.07% / 88.88% |
| 3 years | 90.11% / 90.85% / 91.20% |
| 5 years | 91.12% / 91.59% / 91.72% |
| everything | 91.98% / 92.22% / 92.14% |

One year adds 4.98 points (predicted 2 to 4); three against one +2.32 (predicted 0.3 to 1.0); five
against three +0.52 (predicted -0.2 to +0.3); everything against five +0.50 (predicted -0.3 to
+0.2). Messages ten years old still add to the dictionary instead of misleading it, so the
dictionary keeps all history. The base is 6.7 points below the chat set from Claude Code sessions
(90.61%): Messenger text is harder for the table. Weight 300 beats 1000 only with everything, by
0.08, as predicted.

Result, posts: weight 0 94.34% (105,157 words), a little above the predicted 90 to 94%. The
dictionary from messages adds 1.36 at weight 100 (95.70%), 1.16 at 300 and 0.78 at 1000, inside the
predicted +1 to +3. For posts the best weight is lower than for messages. Some posts may also have
been pasted into messages, which would inflate this gain; not checked.

The crate's weight stays 1000 for now. With a dictionary of years of text, 300 is as good on
messages and better on posts; a weight that falls as the dictionary grows is the next thing to
measure. The messages and posts were deleted from RAM after the run.

## 2026-10-19 · A personal weight that falls as the dictionary grows

Question: weight 1000 was chosen on a dictionary of about 12,000 words; with 1.6 million, 300 did
better on messages and 100 on posts. What weight is best at each size, and does one rule fit them
all? Setup: the same messages and posts, rebuilt in RAM from the export and deleted after the run;
small table (`v2u`, total 534,537,603 tokens); `research.personal TABLE TEST WEIGHTS --learn FILE`.
Message test, last year. Learned from: one year at 10%, 25% and 100% (`--fractions`), three years,
five years, everything, at weights 100, 200, 300, 500, 1000, 2000, 3000 and 10000. Posts, learned
from everything, at 30, 50, 100, 200 and 300. The rule to test: weight = min(1000, T / n), with T
the table's total and n the tokens learned, so that the dictionary never outweighs the table.

Prediction: best weight 1000 to 3000 for one year and its fractions; 1000 to 2000 for three years;
500 to 1000 for five; 200 to 500 for everything; 30 to 100 for posts. The rule scores within 0.1
points of the best weight tried on every message window; on posts it is 0.1 to 0.5 below the best,
since posts are a different register from what it learned.

Result: the falling weight held, the small end missed high. Message test, small table:

| Learned from (words) | Best weight tried | Its score / weight 1000 |
|---|---|---|
| 1 year at 10% (about 6,400) | 10000 | 86.05% / 85.40% |
| 1 year at 25% (about 16,000) | 10000 | 87.19% / 86.62% |
| 1 year (64,133) | 10000, 3000 within 0.01 | 89.37% / 88.88% |
| 3 years (366,370) | 1000 | 91.20% / 91.20% |
| 5 years (766,954) | 1000, 500 within 0.02 | 91.72% / 91.72% |
| everything (1,626,109) | 500, 300 within 0.02 | 92.24% / 92.14% |
| posts, from everything | 100, 30 and 50 within 0.03 | 95.70% / not run |

Three years, five years, everything and posts fall inside their predicted ranges; one year and its
fractions want 10000, not 1000 to 3000. From three years up, the best weight times the words learned
is 3.7 to 8.1 × 10^8, close to the table's total, so the T / n part of the rule fits. Its cap of
1000 does not: it costs 0.5 to 0.65 points on the one-year windows. The chat set from Claude Code
sessions disagrees at the small end ("Tuning the personal dictionary weight": 1000 best, 3000 -0.05
to -0.08, 10000 -0.4). The cap becomes 3000 as a compromise between the two, chosen after seeing
these numbers, so it needs the run below: `auto` in `research.personal` is min(3000, T / n).

Prediction for `auto`: on the message windows from three years up, within 0.1 of the best weight
tried; on one year and its fractions, within 0.05 of weight 3000, so 0.3 to 0.7 above 1000; posts
0.1 to 0.3 below 95.70%. On the chat set from Claude Code sessions (rebuilt in RAM, 5-fold, deleted
after), `auto` within 0.1 below weight 1000.

Speed prediction, written before timing: the weight is now one division per lookup instead of a
constant. `personal_eval` on the frozen wiki runs (`research.crosscheck --lines`), small table,
`main` against this branch, release builds, alternately twice: p99 per syllable with the personal
dictionary differs by less than 10%, within the run-to-run spread.

Result: as predicted on messages and posts; chat missed high. Small table:

| Test, learned from | weight 1000 | `auto` |
|---|---|---|
| messages, 1 year at 10% / 25% / 100% | 85.40% / 86.62% / 88.88% | 85.83% / 86.97% / 89.36% |
| messages, 3 / 5 years | 91.20% / 91.72% | 91.21% / 91.72% |
| messages, everything | 92.14% | 92.22% |
| posts, everything | 95.12% | 95.51% |
| chat, 5-fold (2,750 sentences) | 93.10% | 93.32% |

`auto` equals weight 3000 on the one-year windows (0.35 to 0.48 over 1000), is within 0.02 of the
best weight tried from three years up, and 0.19 below the best on posts. On chat it gains 0.22
instead of losing up to 0.1: the chat set has grown to 2,750 sentences and now agrees with the
messages at the small end. The crate gives the same: `personal_eval` on the chat set (one message
more, 30,834 words) scores 93.32%, as `research.personal ... auto` does on the same file.

Speed, as predicted. Frozen wiki runs, 73,604 syllables, small table, load average 6 to 11 (a
ceiling, not a typical value), p99 per syllable with the personal dictionary: `main` 2.05 and 1.78
ms, this branch 1.87 and 1.99 ms; the difference is inside the spread between rounds. On wiki the
dictionary learned from the other folds scores 96.06% at 1000 and 96.01% at `auto` (3000 there).
The messages, posts and chat set were deleted from RAM after the runs.

## 2026-11-02 · Two readings on mixed Vietnamese and English text

Question: chat in Vietnamese with English words is what makes an input method change `is` into `í`.
On text that dense in English, how many of those words does the small table take back, and how many
Vietnamese words does it break? The 0.99 threshold fixed 138 of 223, 21 of 54, 36 of 98 and 73 of 141
known words and broke none on ordinary text ("Marked words and two readings"), on an older table.

Setup: the small table rebuilt from the recipe in `TABLES.md`. Text: the two reference columns
`chat_lazy` and `synthetic_lazy` of Vikey (github.com/tonyminibot/Vikey, GPL-3), read as data from
outside this repository and not copied into it; none of its code is run. They are the sentences its
author tunes against, so they favour it. Their own output column is 99.81% and 99.92% by whitespace
words, self-published and not reproduced. `research.mixed_readings` types each word in Telex with a
tone at a random place through Ngó Sen's core at default settings (auto-restore on) and
`crates/timsen/examples/mixed_eval` lets the table choose between the core's reading and the raw keys.
Scored lower-cased, by words between punctuation, ignoring tone placement, so the scale is close to
but not the same as the whitespace-word figures 97.63% and 96.17% measured for the core on the same
sentences. A word that only lost a doubled letter (`issue` → `isue`) is the core's bug and is
counted apart; `--core-fixed` scores the text as if the core had fixed it. Personal dictionary off.

Checks: a threshold of 2 never switches, so it must score the core alone, within 0.2 points of the
figures above. The rebuilt table must score within 0.02 of 96.03% on wiki. `readings_eval` runs on
the same text and on wiki, for a figure comparable with the old ones.

Prediction, small table at 0.99. Other changes known to the table: 85 to 95% (common English words),
against 62 to 69% on ordinary text. Of those, 30 to 60% fixed on chat, 40 to 70% on synthetic.
Broken: unlike ordinary text not zero, since a Vietnamese word's keys are often an English word (`có`
as `cos`): 1 to 5 on chat, 5 to 30 on synthetic. Doubled letters: 50 to 80% known, 30 to 60% of those
fixed. Right: chat 98.2 to 98.8%, synthetic 97.2 to 98.2%, and +0.3 to +0.6 more with `--core-fixed`,
so not reaching 99.81% and 99.92%. At 0.9, 10 to 25% more fixes and up to 3 times the breaks.

Result: most held; doubled letters missed low and breaks at 0.9 missed high. Both checks passed: the
rebuilt table has the documented 40,801 words and scores 96.03% on wiki, and a threshold of 2 gives
97.61% and 96.19% against 97.63% and 96.17% by whitespace words. `--core-fixed` at that threshold
gives 98.43% and 96.87%.

| | chat (20,676 words) | synthetic (87,038 words) |
|---|---|---|
| Core alone | 97.61% | 96.19% |
| Doubled letter lost (known to the table) | 169 (103) | 589 (274) |
| Other change (known) | 323 (293) | 2,717 (2,517) |
| 0.5: other fixed / doubled fixed / broken / right | 259 / 14 / 12 / 98.87% | 2,311 / 28 / 18 / 98.86% |
| 0.9 | 216 / 11 / 9 / 98.67% | 1,910 / 13 / 13 / 98.39% |
| 0.99 | 182 / 7 / 1 / 98.52% | 1,633 / 7 / 5 / 98.07% |
| 0.999 | 145 / 4 / 0 / 98.33% | 1,378 / 4 / 3 / 97.78% |
| 0.99, doubled letters fixed in the core | 182 / - / 1 / 99.30% | 1,631 / - / 5 / 98.74% |
| 0.5, doubled letters fixed in the core | 259 / - / 12 / 99.62% | 2,310 / - / 18 / 99.50% |

Against the prediction, at 0.99: known other changes 91% and 93% (held). Fixed of those known, 62%
on chat (just above 30 to 60%) and 65% on synthetic (held). Broken 1 and 5 (held). Right 98.52% and
98.07% (held), and neither reaches the published 99.81% and 99.92%, on a slightly different scale.
Doubled letters: 61% known on chat (held), 47% on synthetic (below 50 to 80%), and only 7% and 3% of
those known fixed, far below 30 to 60%. One guess, not measured: the core's misspelling (`sory`)
scores as `<unk>`, whose pooled count is large, so the real word rarely wins with confidence. The
table is no substitute for fixing this in the core, which gains 0.78 and 0.67 points at 0.99, above
the predicted 0.3 to 0.6. At 0.9, fixes rise 19% and 17% (held); breaks 9 times on chat (missed, up
to 3 times) and 2.6 times on synthetic.

Broken at 0.99: `lát` → `last` once; `mã` → `max` twice, `bú` → `bus`, `lơ` → `low`, `sẽ` → `sex`
once each. Rare, but `sẽ` → `sex` would embarrass, so a stop list or suggestion-only for such words
needs thought before any switch ships. Most common still wrong: `is` → `í` (214 on synthetic, 7 on
chat), `this` → `thí`, `now` → `nơ`, `too` → `tô`, `there` → `thể`.

`readings_eval`, bare engine with no auto-restore, 0.99, comparable with the older entry: wiki fixes
151 of 225 known and breaks 0 on this table (138 of 223 on the older one); chat 242 of 508, broken
0; synthetic 1,719 of 3,189, broken 5. So dense English does not lower the share much at 0.99, but
synthetic is the first text where 0.99 breaks words.

Not measured: a real app, the personal dictionary, the time a switch takes, or how a change to an
already committed word looks to the user. The sentences favour Vikey; they are not typical chat.

## 2026-11-15 · Mixed text through the fixed core

Question: Ngó Sen's core now keeps the doubled letter of English words it knows (ngosen/ngosen#534),
so `issue` no longer comes out as `isue`. The entry above could only simulate that with
`--core-fixed`. With the real core, how right is mixed text, and what is still left for the table?

Setup: as above, with the same table, threshold and sentence files (Vikey commit 6b29780151, the
same byte sizes as on 2026-11-02). The core is ngosen/ngosen at 05e60eaf, which also carries about
250 other changes since the last run, built with its test fakes and the English word list they load.

Checks: the old core's driver, kept from the last run, must again give 97.61% and 96.19% at a
threshold of 2, so the setup is the same. The new driver must keep `issue`, `sorry` and `coffee`,
which the old one turns into `isue`, `sory` and `cofee` (seen before this prediction).

Prediction. Core alone (threshold 2): chat 98.2 to 98.6%, synthetic 96.6 to 97.0%, near the
simulated 98.43% and 96.87%; the core's own count, 493 to 339 wrong words on chat, points the same
way. Doubled letters still lost: at most 25 on chat and 40 on synthetic (the core counts 15 and 24).
Other changes: within 10% of 323 and 2,717. At 0.99: right 99.0 to 99.4% on chat and 98.5 to 98.9%
on synthetic, within 0.3 of the simulated 99.30% and 98.74%; broken at most 3 and 8, and `sẽ` →
`sex` still among them, since the table and the core's reading of `sẽ` did not change.

Result: every part held, and the real fix scores what the simulation did. Checks passed: the old
driver gives 97.61% and 96.19% at a threshold of 2 again, on the same 20,676 and 87,038 words, and
the table still scores 96.03% on wiki.

| | chat | synthetic |
|---|---|---|
| Core alone, old core / simulated fix / fixed core | 97.61 / 98.43 / 98.36% | 96.19 / 96.87 / 96.87% |
| Doubled letter still lost (known to the table) | 15 (14) | 24 (21) |
| Other change (known) | 322 (293) | 2,693 (2,515) |
| 0.5: other fixed / broken / right | 259 / 12 / 99.58% | 2,310 / 18 / 99.51% |
| 0.9 | 215 / 9 / 99.38% | 1,904 / 13 / 99.04% |
| 0.99 | 182 / 1 / 99.24% | 1,631 / 5 / 98.74% |
| 0.999 | 145 / 0 / 99.06% | 1,376 / 3 / 98.45% |

The core's other changes since the last run move nothing here: other changes fall by 1 and 24 and
the table fixes the same words. Breaks at 0.99 are the same six words as before, `sẽ` → `sex`
among them. What is left is mostly English words whose keys spell a Vietnamese word: `is` → `í`
(215 on synthetic), `this` → `thí`, `now` → `nơ`, `too` → `tô`, `there` → `thể`, `has` → `há`, and
`off` → `of`, which the core keeps on purpose. The doubled letters still lost are names and words
outside the core's list (`messi` → `mesi`).

## 2026-11-15 · Near certainty before switching to a crude word

Question: at 0.99 the table changed `sẽ` into `sex` once on synthetic. Such a break costs far more
than leaving an English word as the core read it. Can crude raw readings require near certainty,
and what does it cost?

Setup: as the entry above, fixed core. `Choices::takes_raw` switches to the raw reading when it ranks
first with the caller's threshold, or with `SENSITIVE_CONFIDENCE` (0.9999) for `ass`, `piss`, `sex`
and `tits`. These are the crude words, of about 60 checked, that the core at default settings turns
into a Vietnamese word (`sẽ`, `tít`) or a shorter one (`as`, `pis`); `lust` → `lút` is left out as
not crude. `mixed_eval` now decides through `takes_raw`.

Seen before this prediction, from a one-off probe of the readings: `sex` was the raw reading of 108
words on chat and 241 on synthetic. It ranked first 6 times on chat (confidence 0.667 once, 0.963
five times) and 5 on synthetic (0.963 four times, 0.9988 once), all of them meant as `sẽ`. The two
words meant as `sex`, both on synthetic, ranked `sẽ` first, so the table never fixed them.

Prediction: broken words fall by exactly those counts, 6 and 5 at 0.5, 5 and 5 at 0.9, 0 and 1 at 0.99, 0
and 0 at 0.999, unless `ass`, `piss` or `tits` also occur, which the sentences may not hold. Fixed
English words unchanged at every threshold, since no word meant as one of the four was fixed.

Result: held exactly. Broken words, before and after, chat then synthetic: 0.5, 12 to 6 and 18 to
13; 0.9, 9 to 4 and 13 to 8; 0.99, 1 to 1 and 5 to 4; 0.999, 0 to 0 and 3 to 3. Fixed English words
and doubled letters are the same at every threshold. Right at 0.99 stays 99.24% and 98.74%, one
word on 87,038 too few to move it; at 0.9 it rises to 99.40% and 99.05%. `ass`, `piss` and `tits`
broke nothing before, so these sentences test only `sex`. The floor is set from one break at 0.9988,
so a crude word that the table is surer of still switches; the two words meant as `sex` show it
costs nothing here, but they are too few to say what it costs elsewhere.

## 2026-11-15 · Reading the table into memory instead of mapping it

Question: Ngó Sen does not vendor `memmap2`, and a mapped table changes under the input method when
an update writes over the file in place; the new test
`an_open_table_ignores_its_file_being_rewritten_in_place` panics on the mapped version (an index out
of bounds in `table.rs`). `Table::open` now reads the whole file. What does that cost?

Setup: `cargo run --release --example open_cost TABLE RUNS` on the small table (22,650,872 bytes),
runs from `research.crosscheck` on the wiki test set (11,765 runs), built from `main` (mapped) and
from this branch (read), each run three times, alternating. The table sits in RAM (`/tmp`), so
opening never waits for a disk: a ceiling on what reading costs over mapping is the time to copy
the file, not to fetch it from an SSD, which is not measured here. The large table is not on this
machine. Intel Xeon E5-2696 v4, other jobs running (load average 1.6).

Prediction: opening takes longer when read, 5–30 ms against 1–10 ms mapped. Resident memory after
opening is at least the file size when read (≥ 22 MB) and lower when mapped, since only the checked
sections are touched; after typing every run the two end within a few MB of each other, because the
runs touch most of the table. Later keys: p50 and p99 the same within run-to-run spread. The first
key is no slower when read. The checksum (guessed words) is the same for both builds.

Result: opening missed both ranges, and memory ends the same. Three runs each, mapped then read:
- open: 28.3, 30.4, 26.8 ms mapped; 39.2, 43.8, 39.5 ms read, about 12 ms more;
- resident after opening: 23.0 MB mapped, 28.5–28.7 MB read; after typing every run 31.3–31.4
  against 31.3–31.5, the same;
- later keys (73,603): p50 0.063–0.064 ms and p99 0.635–0.654 ms in both, within the spread;
- first key 0.007–0.010 ms in both; checksum 469,427 guessed words in both.

The mapped table was never cheap to open: checking the sections at open already reads most of the
file, so 23 MB of it was resident before any key. Reading it costs about 12 ms once, off the key
path, and about 6 MB more until typing has touched the rest. Load average rose to 3.6 during the
runs, so the opening times are ceilings.

## 2026-11-15 · The crate inside Ngó Sen's Rust core

Question: can Ngó Sen's typing core (`bamboo-rs`) take the crate as a plain Rust dependency, built
the way Ngó Sen builds itself (vendored crates, `--offline --locked`, its release profile with
`panic = "abort"` and LTO), and call `Table::restore` when a word ends, without breaking its tests?

Setup: a copy of Ngó Sen at commit 05e60eaf in RAM, never pushed. The crate comes from this
repository at ebf8b12 as a git dependency of `bamboo-rs`, vendored with `cargo vendor` next to Ngó
Sen's own crates. The engine gets an optional shared `Table` and keeps the words of the run; every
commit passes through `commit_preedit_and_reset`, which calls `restore` on the run and keeps the
result without showing it, so typing does not change. A new core test types `toi go phim` with
spaces on the fixture table and reads the restored run. Built with
`cmake -DNGOSEN_CORE_ONLY=ON -DBUILD_TESTING=ON -DCMAKE_BUILD_TYPE=Release`, then `ctest` and
`cargo test --release --offline --locked` in `bamboo-rs`; local cargo 1.99 (Rust 1.88 is checked by
the crate's own CI job). Unchanged Ngó Sen, built the same way: 19 of 19 `ctest` tests and 124
cargo tests pass, static library 45,357,324 bytes.

Prediction: `cargo vendor` adds one directory, the crate, which has no dependencies, and changes no
other vendored crate. The build passes offline and locked with no duplicate symbols, since there is
one static library. 19 of 19 and 125 tests pass, the new one restoring `tôi gõ phím`. The static
library grows by less than 1 MB.

Result: held.
- `cargo vendor --no-delete` added `vendor/timsen` and nothing else (`diff -rq` against the vendor
  tree before). `Cargo.lock` gained the crate only. `.cargo/config.toml` needs one more stanza that
  replaces the git source with the vendored one.
- The CMake build passed offline and locked, and the C++ core tests linked against the library: no
  duplicate symbols. `nm` shows the crate's symbols in it.
- 19 of 19 `ctest` tests and 125 of 125 cargo tests pass, including the new one
  (`word_ends_restore_the_run_through_timsen`).
- The static library is 45,925,874 bytes, 568,550 more.

Found on the way:
- Every commit, at a space, a word-break symbol, a macro or a reset, goes through
  `commit_preedit_and_reset` (`src/engine/mod.rs:921`), so the crate is called from one place.
- `reset` is how a focus change or a cursor move reaches the engine; it commits nothing, which is
  where a run must end. This proof never ends a run; the word-end contract does.
- The vendored crate lacks `tests/fixtures/tiny.timsen` and `tiny.runs`; why was not checked (the
  table is tracked through a `.gitignore` exception, the runs file is not ignored at all). Ngó Sen
  does not run the crate's tests, so this costs nothing there; the proof copied the table next to
  its test.
- Source for Ngó Sen: this repository as a git dependency pinned to a commit, vendored with
  `cargo vendor`. Others can build it only once this repository is public.

## 2026-11-15 · Sharing the table, cost per key

Question: `Typing` and `Personal` can now share the table (and `Typing` the dictionary) through
`Arc`, so an input method can keep them in a field with no lifetime. Every lookup now passes
through one more match, borrowed or shared. Does a key get slower?

Setup: `open_cost` as in "Reading the table into memory instead of mapping it" (small table, the
same frozen wiki runs, 73,603 later keys), built from `main` and from this branch, three runs each,
alternating. Both builds borrow the table, the path every caller took before, so this measures the
cost the extra match adds to existing callers.

Prediction: p50 and p99 per key the same within the run-to-run spread of that entry (p99
0.635–0.654 ms); the checksum the same, 469,427.

Result: the same within today's spread, but not within the earlier one, since the machine was busier
(load average 4.7 against 1.6–3.6). Three runs each, `main` then this branch:
- p99: 0.681, 0.689, 0.629 ms against 0.703, 0.665, 0.671 ms;
- p50: 0.069, 0.069, 0.062 ms against 0.070, 0.066, 0.066 ms;
- checksum 469,427 in all six; the two binaries differ.

The ranges overlap (0.629–0.689 and 0.665–0.703), so no cost shows at this precision; a cost of a
few percent would not show either.

A review pointed out that both builds borrowed the table, so the shared path Ngó Sen will use was
not timed. Second run, on this branch only: `open_cost TABLE RUNS HOLD` with each run holding the
table borrowed, through an `Arc` (`Typing::shared`), or with an empty personal dictionary on top,
borrowed (`Typing::with_personal`) or shared (`Typing::with_shared_personal`); three rounds, the four
in turn.

Prediction: `shared` within the spread of `borrowed`, and `shared-personal` within the spread of
`personal`, since an `Arc` is read through one pointer as a borrow is. The personal paths are slower
than the table paths, since each lookup also checks the learned counts. The checksum is 469,427 for
the table paths; with an empty dictionary the guesses are the same, so the personal paths give it
too.

Result: held for the table, not clearly for the dictionary. Load average rose to 7.8. p99 in ms,
rounds 1–3:
- `borrowed` 0.668, 0.661, 0.689; `shared` 0.659, 0.683, 0.678: the same.
- `personal` 0.950, 0.942, 0.943; `shared-personal` 0.968, 1.045, 0.951. Slower in all three rounds,
  and p50 too (0.089–0.091 against 0.092–0.095), so a cost of about 2% may be real; the 1.045 round
  also had one key at 115.7 ms, a stall this run cannot tell from the busy machine.
- checksum 469,427 for all twelve; the personal paths are about 40% slower per key than the table
  alone even when empty.

So sharing costs nothing measurable on the table path and at most a few percent on the dictionary
path, well inside the 3 ms budget; a quiet machine is needed to settle the 2%.

## 2026-11-15 · Latency, memory and the run cap

Question: what does Đoán dấu cost an input method, each part on its own, and how long may a run get
before a key at word end passes the 3 ms budget? The answer sets the run cap.

Setup: `examples/latency.rs TABLE RUNS LEARNED DIR 50 200`, release build, Xeon E5-2696 v4.
- RUNS: the frozen wiki runs of "Reading the table into memory instead of mapping it" (73,604
  syllables, sha256 prefix 81114aca05af2a5e), joined into runs of exactly 50 and 200 syllables:
  73,600 keys each.
- LEARNED: the subs and forum-1..4 test sets, 10,747 lines and 193,263 words with marks (prefix
  292eb5930e969b65), learned into a personal dictionary kept in a file, saved and loaded again.
- A key is what Ngó Sen does when a word ends: `Run::push`, `Run::change(Reach::Run)` and
  `Run::apply`, on a run that reads the dictionary's snapshot.
- Small table (22,650,872 bytes) and large table (`research.prune --bytes 130958840 --min-plain
  1000` from the stored model).
- Memory from `/proc/self/status`: resident after opening and after typing; the peak while a second
  copy of the table is opened in place of the first, as on an update, with the peak reset first.

Prediction, written before any run:
- open: small 30–60 ms, large 150–400 ms;
- personal file 2–6 MB; save 50–300 ms, load 150–600 ms;
- p99 per key, small table: 0.8–2.0 ms at 50, 1.2–3.0 ms at 200; large table: 1.0–2.5 ms at 50,
  1.5–3.5 ms at 200, so the large table at 200 may pass the budget; the last tenth of each run is
  slower than the whole at 200, since each key spells and compares the whole run;
- resident after typing: small 30–60 MB, large 140–200 MB; the reload peak about one table file
  above that;
- the cap: the longest length tried whose last-tenth p99 stays under 3 ms on both tables, expected
  200.

Added after the first two rounds, before running it: since the key cost barely grew from 50 to
200, a third run on the large table at 1,000 and 2,000 syllables (73,000 and 72,000 keys) tells
whether the cap could be longer. Prediction: last-tenth p99 2.3–3.0 ms at 1,000 and 2.4–3.3 ms at
2,000, since each key spells, copies and compares the whole run.

Result: within the 3 ms budget everywhere, but the prediction missed in four places. Two rounds,
small then large in turn; load average 3.9–8.2 throughout, with a backup (`restic`, about 1.2 of the
44 hardware threads) running and, in round 1, this session's own builds; so these are ceilings.
An earlier round was thrown away: its checksum counted letters, which marks do not change, so runs
of 50 and of 200 gave the same number; it is now an FNV hash of the shown text, which differs
between lengths and repeats exactly across rounds. The reload peak in that round was also read
before the dictionary was reopened.

| | small | large |
|---|---|---|
| open | 42.6, 39.7 ms | 175.1, 149.4 ms |
| resident after opening | 25.7 MiB | 141.6–141.7 MiB |
| personal file (193,263 words) | 5.2 MB; save 191, 201 ms; load 728, 837 ms | 5.2 MB; save 195, 167 ms; load 711, 700 ms |
| p99 per key, runs of 50 | 2.008, 2.184 ms | 2.417, 2.246 ms |
| p99 per key, runs of 200 | 2.057, 2.048 ms | 2.488, 2.366 ms |
| last-tenth p99, runs of 200 | 2.010, 2.013 ms | 2.441, 2.279 ms |
| resident after typing | 59.3, 60.1 MiB | 175.7, 176.1 MiB |
| reopening; peak during it | 33.1, 28.0 ms; 91.3, 90.1 MiB | 167.3, 159.3 ms; 320.7, 322.8 MiB |

Against the prediction:
- open: as predicted for the small table; the large one opened in 149.4 ms once, just under the
  150–400 range;
- the personal file: size and save as predicted; loading took 700–837 ms against 150–600, a miss.
  It is off the key path, and Đoán dấu can run on the table alone until it is loaded;
- p99 per key: the small table at 50 came out at 2.0–2.2 ms against 0.8–2.0, a miss on the high
  side; the other three were in range, all under 3 ms;
- the last tenth of a run of 200 was slower than the whole at p50 (0.327–0.401 against 0.295–0.361
  ms) but not at p99, which it was predicted to be: the slow keys come from candidate lists and the
  dictionary, not from the run's length;
- resident after typing: the table gives MiB (the example read kB as KiB), while the prediction was
  in MB. In MB the small table took 62.2 and 63.0, over 30–60 in both rounds, a miss; the large one
  took 184.2 and 184.7, in range. The reload peak is one table and one dictionary above that (about
  30 MiB small, 145 MiB large), as predicted;
- the slowest key was 6.4–12.3 ms in every series: rare (p99 is under 2.5 ms), but over the budget.
  This run cannot tell such stalls from the busy machine.

Runs of 1,000 and 2,000 on the large table, load 7.7–9.3: last-tenth p99 2.494 and 2.698 ms, both in
the predicted ranges; p50 of the last tenth grows from 0.401 ms at 200 to 0.583 and 0.817 ms, about
0.2 ms per 1,000 syllables.

The cap: the rule in the prediction picks 200 from the lengths it named, and the later run shows the
budget would hold even at 2,000. `MAX_RUN` is 200 all the same: no run of the wiki test set is longer
than 61 syllables (p99 27, p99.9 40, `awk '{print NF}'` over the frozen runs), so the cap is almost
never reached, and at 200 the run's own length adds about 0.04 ms to a key, leaving the margin to a
slower machine.

Tests for the cap, predicted before running (`cargo test --no-fail-fast --lib --test run_props`,
one defect at a time): one syllable of context instead of two, 3 red; backspace reaching the
context, 2; the context not skipped in the guess, 4. The first run gave 1, 3 and 4: the two unit
tests could not tell one syllable of context from two on the fixture table, and the property test
asked for a second run even when the text was exactly 200 syllables long, which shrinking found.
With the unit tests checking the context itself and the text at least 201 syllables, the run gave
3, 2 and 4.

### Words read two ways

A review pointed out that every key above came from `Run::push`: a word pushed with two readings
(`Run::push_either`, `tét` or `test`) makes each later key in the run also ask `Typing::choices`,
a backward pass from that word to the end of the run, so its cost grows with the run. Setup as
above with LENGTH `50x` and `200x`: one word in 20 pushed with a second reading (the word plus `s`),
large table first. The example now gives memory in MB, as the prediction was written.

Prediction, before running: this path passes the budget. p99 per key 3–8 ms at 50 and 10–40 ms at
200, the last tenth of a run the slowest.

Result: a miss, far over the predicted range. On the large table, load 7.6–9.3, runs of 50 gave
p50 8.1, p95 23.3, p99 30.6 and max 50.3 ms over 73,600 keys; runs of 200 did not finish in ten
minutes and were stopped. The prediction took the backward pass to cost about as much as a key's
forward step; it costs ten times as much, and every key after the first word read two ways pays
for it back to that word. Most of the `+s` readings are not words the table knows, so this was the
pass alone, not a real choice.

### Words read two ways, decided in a window

The fix: a word read two ways is weighed on each key only while it is among the last four
syllables (`WINDOW` in `run.rs`); when the next word pushes it out, its reading is decided once
and kept, and backspace back into the window weighs it again. A key then pays for at most four
syllables of backward pass whatever the run's length.

The readings are now real: the word's two likeliest spellings alone (`Typing::choices` on the word
by itself, for instance `gõ` and `gỗ`), both words the table knows, so the context really decides.
Words with one spelling are pushed as usual. The example also counts, for each such word, whether
the run ends with the reading that weighing the whole run at its end gives (`Typing::choices` over
the whole run on a parallel `Typing`), at raw confidence 0.99 and 0.5.

Prediction, before running, for `50x` and `200x` on both tables:
- p99 per key 2.5–4.0 ms on the large table, 2.0–3.5 ms on the small one, and no higher at 200
  than at 50 (within 0.3 ms);
- agreement with the whole run at least 99% at 0.99 and 98% at 0.5; the raw reading kept at least
  once at 0.5, or the count shows nothing;
- the instrument: a build with `WINDOW` 1 agrees less, by at least half a point at 0.5 on the
  large table.

Result: in range everywhere except the last tenth of runs of 50, which went over the budget. Load
2.5–5.2, so these are ceilings again.

| | small | large |
|---|---|---|
| p99 per key, runs of 50 | 2.563 ms | 3.317 ms |
| p99 per key, runs of 200 | 2.660 ms | 3.149 ms |
| last-tenth p99, runs of 50 | 3.666 ms | 4.802 ms |
| last-tenth p99, runs of 200 | 2.447 ms | 2.919 ms |
| agree with the whole run, 0.99 (50; 200) | 4,104/4,105; 3,435/3,436 | 4,102/4,105; 3,433/3,436 |
| agree with the whole run, 0.5 (50; 200) | 4,105/4,105; 3,436/3,436 | 4,103/4,105; 3,435/3,436 |

- The cost no longer grows with the run: p99 at 200 is within 0.2 ms of p99 at 50 on both tables.
  The last tenth of a run of 50 is slower only because of where the words fall: two readings sit
  at every 20th syllable from the fourth, so three of a 50-run's last five keys weigh one in the
  window, against four of a 200-run's last twenty.
- The large table is over the 3 ms budget at p99 when words are read two ways (3.1–3.3 ms), against
  2.2–2.5 ms without them. One word in 20 with two real readings is more than typed Vietnamese
  usually holds, so this is a worst case.
- Agreement is 99.9% or more, and the raw reading was kept 524–982 times, so the count does see a
  choice. The instrument: a build with `WINDOW` 1 agrees on 3,942 of 4,105 at 0.5 (96.0%) and 4,001
  at 0.99 on the large table, runs of 50, against 4,103 and 4,102 at 4: four points lower, past the
  half point predicted. It is also cheaper (p99 2.255 ms): the window trades speed for agreement,
  and 4 keeps agreement while holding the key near 3 ms.

Tests for the window and the context, predicted before running (`cargo test --no-fail-fast --lib
--test run_props`, one defect at a time): the context guessed again (`push` in place of
`push_context`), 1 red; no window (every word weighed on every key), 1; a word never decided when it
leaves the window, 1.
The run gave 1, 1 and 1, each in the named test.

## 2026-11-15 · Integration proof: the final API inside Ngó Sen's core

Question: does the crate's final API fit Ngó Sen's typing core the way step 6 meant it to, through
its word-end and private-field paths, built the way Ngó Sen builds itself? Specifically: one
`Dictionary` shared by every field, a `Run` per field on its snapshot, `Run::push` or
`push_either` at each word end, a `Change` per word end, learning at a run's end, the cap, and a
private field that never reaches the crate.

Setup: the copy of Ngó Sen at 05e60eaf from "The crate inside Ngó Sen's Rust core", in RAM, never
pushed. The crate comes from this repository at 8196fc7 (main after #60) as a git dependency of
`bamboo-rs`, vendored with `cargo vendor --no-delete`. In `bamboo-rs/src/engine/mod.rs` the proof
replaces the earlier `Table::restore` call:
- the engine holds an optional `Diacritics`: the `Arc<Mutex<Dictionary>>` all fields share, this
  field's `Run`, the words as committed, and the changes for the front end to apply. The lock is
  held only to take a typing or to learn, never while restoring;
- every commit goes through `commit_preedit_and_reset`. Each word in it is pushed, with two
  readings when the keys differ from the text and are plain letters (`tét`, `test`). A commit that
  holds anything but letters and spaces, or none at all (a reset: focus change or cursor move),
  ends the run with `change(true)`; otherwise `change(false, Reach::Run)`. Each change is applied
  and queued;
- at a run's end, or at the cap before the next word, the words typed with marks are learned and
  the rest passed as `None`; a full run goes on with `Run::next(dictionary.typing())`;
- `set_private(true)` ends the run without learning, and while private nothing reaches the crate.
Five core tests replace the earlier one, on the fixture table: a run's changes bring the field to
`tôi gõ phím`; punctuation ends a run and learns its marked words; a private field sends nothing
and drops what waited to be learned; two engines share one dictionary, so what one field learns
the next run in another restores; 201 words go on past the cap. Built with Ngó Sen's CMake path as
before (`-DNGOSEN_CORE_ONLY=ON -DBUILD_TESTING=ON -DCMAKE_BUILD_TYPE=Release`, vendored,
`--offline --locked`, release profile with `panic = "abort"`), then `ctest` and
`cargo test --release --offline --locked` in `bamboo-rs`. Saving the personal file is left out:
it runs from the owner off the key path and has its own tests here.

Prediction, before building:
- `cargo vendor` changes only `vendor/timsen`; `Cargo.lock` changes only the crate's revision; the
  crate still has no dependencies;
- the build passes offline and locked, with no duplicate symbols;
- 19 of 19 `ctest` tests and 129 of 129 cargo tests (124 of Ngó Sen's, five new) pass;
- the static library grows by less than 1.5 MB over unchanged Ngó Sen (45,357,324 bytes);
- the tests see the paths: ignoring the private flag turns 1 test red (the private one); not
  ending a run at punctuation turns 2 red (learning at punctuation, two fields sharing).

Result: held, after one fix the prediction did not foresee.
- `cargo vendor` changed only `vendor/timsen` (`diff -rq` against the tree before), and
  `Cargo.lock` only the crate's revision.
- The CMake build passed with vendored sources and `--offline`, release profile with
  `panic = "abort"`, and the C++ core tests linked against the library: no duplicate symbols.
- 19 of 19 `ctest` tests and 129 of 129 cargo tests pass (4 of Ngó Sen's ignored, as before).
- The static library is 46,234,810 bytes: 877,486 more than unchanged Ngó Sen, 308,936 more
  than with the earlier link proof.
- The tests see the paths: ignoring the private flag turned exactly the private test red; not
  ending a run at punctuation turned exactly the two predicted tests red.

Found on the way:
- A `Change` counts syllables from the start of its run, but a field knows only where the cursor
  is, and a run may begin anywhere before it. The first run of the tests applied changes at the
  wrong place. The engine now hands the front end each change with the number of words between it
  and the cursor (`Run::len` minus the change's end); the crate's API had what was needed.
- The keys of a word, as the engine holds them at the commit, end with the key that ended it
  (`test ` with its space), so no word ever took the two-readings path until they were trimmed.
  A probe (a print in the copy, removed afterwards) showed `tét`/`test`, `mở`/`mowr`, `là`/`laf`
  and `có`/`cos` pushed with two readings once trimmed, and none before. None of the five tests
  can see this: on the fixture table no raw reading wins at confidence 0.99. A test that does
  belongs with step 7, on the real table.
- Every word typed with Telex marks has keys that differ from its text, so every such word reaches
  the crate with two readings, not only English words the engine kept as typed. The confidence
  threshold and the crude-word list are what keep `có` from turning into `cos`.
- Nothing calls the new engine functions yet (the C API comes in step 7), so the library build
  warns of dead code three times. Ngó Sen's own CI, which denies warnings, would need the calls
  first.
- The patch against unchanged Ngó Sen is kept in RAM (`/tmp/ngosen-diac/linkproof/integration.patch`,
  261 changed lines), not in this repository: Ngó Sen's code goes into Ngó Sen in step 7.

Review of the proof (Codex), every finding checked against the copy and fixed there:
- a word half typed when the field turned private reached the crate at its commit and was learned;
- a reset (a cursor move) ended the run with a change counted from a cursor that had moved;
- Enter, Tab, and a symbol after a space are forwarded without a commit, so the run went on across
  them unlearned;
- a commit of several words across the cap left the full run's last word unrestored;
- a change pulled after a later commit was counted from the later cursor;
- a word typed with marks whose raw reading replaced it was learned in its interpreted form;
- a digit stayed inside a word (`toi1`) instead of splitting it and ending the run;
- the lock was held while `Run::next` scored its context.
Six tests were added, eleven in all; the copy now passes 135 of 135 cargo tests (124 + 11).

Prediction, before running, one defect at a time (`cargo test --offline --locked --no-fail-fast`):
the half-typed word not skipped, 1 red; a reset that ends with a change, 1; no end at a forwarded
key, 1; no change before the cap moves on, 1; digits kept inside words, 1; the raw reading learned
anyway, 0, since no raw reading wins on the fixture table at 0.99.

Result: as predicted, 1, 1, 1, 1, 1 and 0, each in the test named for it. The last defect is not
seen by any test, as said; it waits for a test on the real table in step 7. The full build again,
after the fixes: 19 of 19 `ctest` tests and 135 of 135 cargo tests, static library 46,232,080 bytes
(874,756 more than unchanged Ngó Sen), the same three dead-code warnings. The patch kept in RAM is
now 400 changed lines. What step 7 takes from the review: the front end applies the changes before
it forwards the key that made them, and a cursor move drops any change not yet applied.

A second review found two more, both fixed in the copy with a test that failed before the fix: a
commit holding a separator inside it (a macro `ban thich go. phim`) was scored as one run, and the
privacy skip outlived a half-typed word that `rebuild_from_text` replaced, swallowing the next
public word. Prediction, before running, one defect at a time: no end at a separator inside a
commit, 5 red (punctuation, two sentences, digits, two fields, reset); the skip not cleared on
rebuild, 1; digits kept inside a word, 1.

Result: 4, 1 and 0, two misses. The digits test did not turn red under either defect: Telex
forwards a digit typed after a word (`toi1`) instead of committing it, so that test goes through
the forwarded-key path and never reaches the splitting. A test that commits a digit inside the
text directly (`ban thich go1`, as a macro can) was added. Prediction for it: red under the digit
defect (1), and red under the separator defect too (5).

Result: 5 and 1, as predicted. The full build after both reviews: 19 of 19 `ctest` tests and 138
of 138 cargo tests (124 of Ngó Sen's, 14 new), static library 46,238,432 bytes (881,108 more than
unchanged Ngó Sen), the same three dead-code warnings; the patch kept in RAM is 453 changed lines.

A narrow review of the privacy fix found it leaked still: the skip was spent at the first commit,
so a private word reopened after it (Backspace, or the front end rebuilding it) reached the crate
and was learned, and the internal Backspace rebuild cleared the skip. Clearing it only on an empty
rebuild closed one path and left the others, so the rule changed instead: a field that has been
private stays off for good; Ngó Sen keeps one engine per field, so this lasts until the field goes
away. The cost is Đoán dấu in a field that shows a password and then turns back, which should not
learn anyway. The test for a public word after a replaced private one went, and one for a word
reopened after its commit came in.

Prediction, before running: turning back on when the field turns public, 4 red (the four privacy
tests); the private flag not checked at a commit, 4.

Result: 4 and 4, as predicted. The full build after every review: 19 of 19 `ctest` tests and 139
of 139 cargo tests (124 of Ngó Sen's, 15 new), static library 46,238,344 bytes (881,020 more than
unchanged Ngó Sen), the same three dead-code warnings; the patch kept in RAM is 464 changed lines.
The figures above for 135 and 138 tests are superseded.

## 2026-11-15 · Fixing unknown syllables in the crate, decided when a word ends

Question: "Fixing syllables the table does not know" scored a fix with the whole sentence around
the syllable. An input method decides when the word ends, with only the words before it. Is the fix
still safe and useful decided that way, at margin 4? And does the crate decide exactly as
`research.typo` does, without passing the 3 ms budget per key?

Setup:
- `research.typo --typing` scores each syllable on the run up to it, not over: no right context
  and no end of run (`Model.restore` and `local_score` take `ended=False`). Without the flag it is
  the whole-run fix of the earlier entry, unchanged.
- Small table, test sets `wiki` and `subs` as in the earlier entry, and `forum-1..4` (forum-1 to
  forum-4 joined: 6,747 lines, 160,836 words, sha256 prefix 83a922cc46cae3a0), which is not the
  earlier `forum` set, so its whole-run figures are new too. Same typo model and seed as before.
- The crate: `Typing::fix(i, ended)` mirrors `best_fix`; `Run::push` fixes the word that just
  ended when the fix wins by the margin set with `Run::fixing` (off by default, as the plan
  promises; `FIX_MARGIN` is 4), and `Run::undo_fix` takes the latest fix back for good. A word the
  personal dictionary knows is never a target.
- Crosscheck: `research.typo --write-fixes` writes every decision, both ways, on the clean runs
  and the mistyped copies of `wiki` and `subs`; `examples/fix_check.rs` recomputes each with the
  crate, on the small and the large table.
- Latency: `examples/latency.rs` as in "Latency, memory and the run cap", runs of 50 and 200, both
  tables; every push may now fix.

Prediction, written before any run:
- whole run, small table, margin 4: `wiki` and `subs` repeat the earlier figures exactly
  (0.001% / 41.5% / 99.5% and 0.009% / 46.4% / 99.6%), since only a default argument changed;
- decided when the word ends, margin 4: fewer typos fixed, for lack of the words after: 30–38% on
  `wiki`, 35–42% on `subs`, 28–36% on `forum-1..4`; at least 97.5% of fixes right; clean words
  changed no more than with the whole run (≤ 0.02%). Margin 4 still meets both limits (≤ 0.05%
  clean, ≥ 98% right) on `wiki` and `subs`; `forum-1..4` may fall just under 98% right;
- crosscheck: every decision the same fix, none on the other side of the margin, margins within
  1e-9, on both tables;
- latency: p99 per key grows by less than 0.3 ms over the earlier 2.0–2.5 ms and stays under 3 ms.
- the crosscheck sees a defect: built once with `local` never adding the end of run, the fixture
  test fails and `fix_check` on the small table still agrees on every `typing` decision but shows a
  margin difference above 0.01 on `ended` ones; built once with no deletions among the candidates,
  the fixture test fails on the fixes that drop a letter (`quyy`, `Tooi`, `noii`) and `fix_check`
  reports decisions that differ in both modes.

Result, small table, margin 4 (clean words changed / typos fixed right / share of fixes that are
right), load average 5.8–7.1:

| Set | Whole run | Decided when the word ends |
| --- | --- | --- |
| wiki | 0.005% / 45.1% / 99.4% | 0.005% / 23.9% / 99.5% |
| subs | 0.009% / 49.9% / 99.4% | 0.006% / 24.8% / 98.7% |
| forum-1..4 | 0.015% / 45.1% / 98.6% | 0.009% / 23.2% / 98.0% |

Against the prediction:
- whole run: missed. `wiki` and `subs` do not repeat the 2026-10-17 figures (`wiki` 45.1% fixed
  right against 41.5%; 42.4% of typos landing on a known form against 41.6%). The code is not the
  cause: `research.typo` from `main` prints the same figures, line for line, on today's files. The
  test files or the small table were rebuilt since that entry, which recorded neither checksum, so
  its figures cannot be reproduced; these are the reference now.
- decided when the word ends: safety as predicted, usefulness missed. Clean words changed fell
  (0.005–0.009%) and fixes stay right 98.0–99.5% of the time, so margin 4 meets both limits on all
  three sets, `forum-1..4` exactly at 98.0%. But only 23–25% of typos are fixed right, not 30–42%:
  without the words after it, half of the fixes the whole run makes no longer win by 4. A lower
  margin does not buy them back safely: at margin 3, `subs` falls to 96.9% right.
- crosscheck: as predicted. 28,368 decisions on `wiki` and `subs` (each unknown syllable of the
  clean runs and the mistyped copies, both ways): every one the same fix, none on the other side of
  the margin, largest margin difference 0, on both tables. Made at the margin: small table 2,209
  while typing and 4,193 with the whole run, large table 2,235 and 4,148.
- the crosscheck sees a defect: as predicted. With `local` never adding the end of run, the fixture
  test fails and `fix_check` differs on 369 decisions, all with the whole run and none while typing
  (216 on the other side of the margin, margin off by up to 7.08). With no deletions among the
  candidates, the fixture test fails and the fixture's decisions differ on exactly `quyy`, `Tooi`
  and `noii`, both ways; not predicted, one fix that stays the same moves its margin by 3.18, since
  its runner-up was a deletion, and that is where the test failed first. Rebuilt without a defect,
  all 28,368 agree again.
- latency: two rounds, `main` (no fixing) then this branch (fixing on) in turn, small then large;
  the shown text hashes differ between the two, so fixes were made. Added after round 2, before
  running it: in round 2 the branch on the large table at 200 had p99 2.873 ms against 2.270 ms,
  with p50 up 26% as well, which looks like load rather than fixing; two more rounds on the large
  table alone decide it. Prediction: in both, the branch's p99 within 0.3 ms of `main`'s.

  p99 per key, ms (`main` / branch), load average 1.7–7.0:

  | Round | small, 50 | small, 200 | large, 50 | large, 200 |
  | --- | --- | --- | --- | --- |
  | 1 | 2.052 / 1.914 | 2.001 / 2.003 | 2.197 / 2.149 | 2.208 / 2.204 |
  | 2 | 2.012 / 1.911 | 2.040 / 1.973 | 2.195 / 2.423 | 2.270 / 2.873 |
  | 3 | | | 2.336 / 2.226 | 2.279 / 2.229 |
  | 4 | | | 2.246 / 2.448 | 2.330 / 2.340 |

  As predicted: in rounds 3 and 4 the branch is within 0.3 ms of `main` (−0.11 to +0.20), so round
  2 was load; every p99 stays under 3 ms, the highest 2.873 ms in that round. Fixing costs nothing
  measurable here, but these runs are clean text: only the 3% of syllables the table does not know
  are scored for a fix at all, so a writer with many typos pays it on more keys than this shows.

Conclusion: the crate fixes exactly what `research.typo` fixes and stays within the key budget.
Decided when the word ends, margin 4 is safe on all three sets but fixes about a quarter of the
typos it can see, half of what the whole run fixes; the words after a typo carry the other half.
Fixing stays off by default, as planned; step 7 decides whether it is offered on.

## 2026-11-15 · The integration proof again, with fixing

Question: step 5 changes what a word end does, so the integration proof of "The crate's final API
inside Ngó Sen's core" runs again on it. Do its tests still pass on the new crate, with fixing off
(the default) and with it on, and does a typo reach the field fixed through Ngó Sen's own key path?

Setup: the same copy of Ngó Sen in RAM, never pushed, with the glue of that entry. The crate's
revision moves from 8196fc7 to c5e2c8d (main after #62), vendored again with `cargo vendor
--no-delete`; built and tested exactly as there (CMake core build, `ctest`, `cargo test --release
--offline --locked` in `bamboo-rs`). Then a second build with the glue's `Run::new` followed by
`.fixing(Some(FIX_MARGIN))` and one more test: typing `toi go phmi` and a space each, through
Telex, brings the field to `tôi gõ phím`.

Prediction, before building:
- `cargo vendor` changes only `vendor/timsen`; `Cargo.lock` only the crate's revision;
- fixing off: the build passes offline and locked, 19 of 19 `ctest` tests and 139 of 139 cargo
  tests pass, and the static library grows by less than 100 KB over 46,238,344 bytes;
- fixing on: 19 of 19 and 140 of 140, no test of the earlier proof changes, since none of them
  types a syllable the fixture table does not know; the new test passes;
- the new test sees fixing: with `.fixing(None)` in the glue it is the one test that fails.

Result: held, but for one test the prediction did not foresee.
- `cargo vendor` changed only `vendor/timsen` (13 files, `diff -rq` against the tree before), and
  `Cargo.lock` only the crate's revision.
- Fixing off: the CMake build passed vendored, offline and locked; 19 of 19 `ctest` tests and 139
  of 139 cargo tests pass, with the same three dead-code warnings. The static library is
  46,357,146 bytes, 118,802 more than before: over the 100 KB predicted, since the fixing code is
  compiled in whether a run uses it or not.
- Fixing on: 19 of 19 `ctest` tests, but 139 of 140 cargo tests, not 140. The test that two
  fields share one dictionary failed at its first step: the fixture table lacks `ngo`, which is one
  edit from `go`, so `ngo sen` was fixed to `gõ sen` before anything was learned. That is the risk
  measured above as clean words changed (0.005–0.009%), met here because the test types a name the
  table does not know. Its second step holds with fixing on: once the other field has learned
  `ngó`, the word is a dictionary word, no longer a target, and comes back `ngó sen`. The test now
  says so (`gõ sen` first, then `ngó sen`); with that, 140 of 140 pass. The library is 46,357,330
  bytes.
- The new test sees fixing: with `.fixing(None)` in the glue it is the one test that fails, as
  predicted. That ran before the shared-dictionary test was changed; on the final tests, fixing
  off turns two red, that test and the new one (predicted 2 before running, and 2).

The copy keeps fixing on; whether Ngó Sen offers it on by default is step 7's question, and this
proof is one input to it: a name the table lacks is fixed until the dictionary learns it. The glue
does not call `Run::undo_fix` yet, and the run that made a fix is gone once a punctuation mark
ends it, so a key to undo a fix, and how long it stays available, are step 7's work too. The patch kept in RAM is now 539 lines (531 before).

## 2026-11-15 · Undoing a fix, prepared in the copy of Ngó Sen

Question: step 7 needs a key that undoes a fix, and a switch for fixing. Can the glue in the copy
of Ngó Sen do all of it but bind the key, with the crate's `Run::last_fix`, `Run::undo_fix` and
`Run::push_as_typed`? Ngó Sen itself is not changed.

Setup: the copy and glue of "The integration proof again, with fixing", built and tested as
there; the crate from this branch. `BambooEngine::set_fixing` (and `EngineSetFixing` for the C++
front end) switches fixing for runs started afterwards, the run after the cap included.

First design: `undo_fix` replaced the fixed word in place with what was typed, any time until the
next word, also after the punctuation that ended its run (kept, learned, until the next word); the
undone word was learned as typed. Five tests. Prediction, one defect at a time (`cargo test
--release --offline --locked --no-fail-fast`): undo not limited to the last word, 1 red; the undone
word not learned in an open run, 1; the ended run not kept, 1; the word undone after its run ended
not learned, 1. Result: 1, 1, 1 and 1, each in the test named for it. Review (Codex) found that a
key forwarded in between, such as Home, left the undo possible with the cursor elsewhere, and that
the run after the cap kept the old fixing setting.

Second design, after the owner chose Backspace, as Ngó Sen already does it: Backspace right after
Space split or shortened a word reopens the word as typed (`restoreDroppedWord`). So undo is now
for the next key only (`fix_undoable`, as `drop_kept_tail`): `BambooEngine::undo_fix` (and
`EngineUndoFix`) takes the fixed word out of the run, reopens it in the preedit as typed, and
returns it as the field shows it, for the front end to delete with the key that ended it. Committed
again unchanged, it is pushed with `push_as_typed` and learned as typed; changed, it is guessed
afresh. After the punctuation that ended the run, the run goes on without learning its words
twice. Binding Backspace to `EngineUndoFix` in the front end (`ngosen-state.cpp`, before
`restoreDroppedWord`) is step 7's. Seven tests replace the five: reopen after a space, committed
again as typed and learned; the same after punctuation, the run going on; a reopened word changed
is guessed afresh; no undo with nothing typed, nothing fixed, a word or another key after the fix,
after a reset, or twice; none in a private field; the switch from the next run, and past the cap.

Prediction, before running, one defect at a time: undo not limited to the next key, 1 red (the
test for when undo applies); the reopened word committed again guessed as usual, 2 (both reopen
tests); the reopened word not learned, 2 (the same); the run after the cap ignoring the switch, 1;
words learned again after a reopen past punctuation, 0, since no test counts what is learned.

Result: 1, 2, 2, 0 and 0. The miss was the switch past the cap: its test put `toi go` before the
cap and `phmi` after it, where nothing is fixed with the switch on either, so it could not fail.
Rewritten to type `toi go phmi` after a full run, once with fixing on (fixed) and once off (kept),
it fails with that defect: 1, 2, 2, 1 and 0 on the rerun, each in the tests named above. The
copy builds with the CMake core build (`NGOSEN_CORE_ONLY=ON`, Release): 19 of 19 `ctest`, 147 of
147 `cargo test --release`, the same four dead-code warnings as before, for glue the front end
does not call yet.

Review (Codex) of the second design found four problems, each checked in the code. Undo was
armed by any key that committed text while the run still ended in the fixed word, so a second
Space, or Home pressed with the word still being typed (committed, fixed, and the key passed on
to move the cursor), left it possible. A change not pulled yet was dropped whole by an undo,
the fixes of the words before included. The text to delete was assumed to be the word and one
key, which a Tab macro (nothing after the word) and a macro ending in punctuation (`phím. `)
break. And the crate's `Run::apply` let a change taken earlier overwrite a word kept as typed;
fixed in the crate (`apply` refuses a change that alters a kept word) and vendored. Third
design: undo is armed only by a key the engine used whose commit ends in the fixed word; it is
refused while changes wait to be applied; it returns the text from the fixed word to the cursor
(`phím `, `phím.`, `phím` after a Tab macro), which the front end checks before the cursor and
deletes, as `restoreDroppedWord` does. Tests: the second Space and Home while typing in the test
for when undo applies; the text to delete after a space, punctuation and a Tab macro; no undo
while the fix waits, and the fix still applied after.

Prediction, before running, one defect at a time: undo armed by a key passed on to the app, 1
red (the test for when undo applies); a commit without a word leaving the last tail, 1 (the
same); the tail left out of the returned text, 1 (the text-to-delete test); undo allowed while
changes wait, 1 (that test); a key that ends the run not clearing the tail, 0, since such keys
are passed on and already refused. The five defects of the second design again: 1, 2, 2, 1, 0.

Result: 0, 2, 2, 1, 0 for the five, and 0, 0, 1, 1, 0 for the new ones: three misses, the undo
limited to the next key, a key passed on, and a commit without a word. Each check is backed by
another in the cases tested: Home and a second Space with macros off are passed on, which ends
the run and clears the tail. Cases only one check covers, added to the test for when undo
applies: a letter typed after the fix (only the next-key flag), Tab without a macro, which the
engine passes on without ending the run (only the key passed on), and a second Space with macros
on, which the engine commits (only the tail cleared). Prediction for the rerun: 1, 2, 2, 1, 0
and 1, 1, 1, 1, 0.

Result: 1, 2, 2, 1, 0 and 0, 1, 1, 1, 0: the key passed on missed again. Every key the engine
passes on after a commit, Tab without a macro included, goes through the branch that ends the
run and clears the tail, so that check could never act; it is removed, and clearing the tail
there is the one check left for such keys. Prediction for the rerun without it: 1, 2, 2, 1, 0,
then for the tail 1 (a commit without a word), 1 (left out), 1 (changes waiting) and 1 (a key
that ends the run), each in the tests named above.

Result: as predicted, 1, 2, 2, 1, 0 and 1, 1, 1, 1, each in the test named for it. With the crate
fix vendored, the copy builds as before: 19 of 19 `ctest`, 149 of 149 `cargo test --release`, the
same four warnings.

A second review (Codex) found four more, each checked in the code; the first is the undo's, the
others are older gaps in the glue that the undo made easier to reach. The returned text was in
Unicode while the field may use another charset (VIQR shows `phi'm`). Backspace with nothing
being typed goes to the app, which deletes the end of the run, but the run went on as if the
field still held it. `EngineRebuildFromText`, which the front end calls whenever it takes a word
back from the field (retyping, a new tone, Backspace into a word, the reopen after Space), left
the run going and an undo armed. And rebuilding a kept word types keys again inside the engine,
whose commits Đoán dấu took for typing. Fourth design: the text is encoded as committed text is;
that Backspace and a word taken back end the run without changing anything, as a reset does;
the engine's own rebuilds (the undo, Backspace within a kept word) keep the run, and Đoán dấu
does not see the keys they type again.

Prediction, before running, one defect at a time, each 1 red in its new test: the word taken
back not ending the run; Backspace to the app not ending it; the text left in Unicode; the keys
of a rebuild seen by Đoán dấu. The nine before: 1, 2, 2, 1, 0, 1, 1, 1, 1.

Result: 1, 0, 1, 0, then 1, 2, 2, 1, 0, 1, 1, 2, 1, 1; three misses. With macros off, Backspace with
nothing typed goes the way of any key passed on, which already ends the run, so its test did not
reach the gap; with macros on the engine handles Backspace itself, and the test now turns them on.
Leaving the tail out also fails the new charset test, which compares the whole text: 2, not 1. A
probe showed that rebuilding `hòa2` or `tôid2` does commit inside the engine, but the text ends in a
digit, which ends that run at once; it is dropped at the next word with nothing learned or changed,
so no test sees it. The check stays, since Đoán dấu should see only text the field gets, without a
test that shows it acting. Prediction for the rerun of the Backspace defect: 1. Result: 1. The test
for the rebuild, which could not fail, is dropped. The copy builds: 19 of 19 `ctest`, 152 of 152
`cargo test --release`, the same four warnings; it differs from Ngó Sen only in the glue's lines.

A third review (Codex) found two more. In Sen mode the front end resets the engine after every
word it commits (`commitWord`, after `EnginePullCommit`), which ends the run and drops its
changes before they are pulled: the binding in step 7 must pull and apply the changes first and
must not end the run there, or Đoán dấu does nothing in Sen mode. That is the front end's, so it
goes to the plan. And the front end also rebuilds the word being typed (Backspace that removes a
tone, and the fallback for keys shown as typed), where ending the run loses the words before
it; a rebuild now ends the run only when nothing is being typed, so the text came from the field.
Prediction, before running: ending the run on every rebuild, 1 red (the new test: a tone removed
from the word being typed keeps the run); the defects before unchanged: the word taken back 1,
Backspace to the app 1, the text in Unicode 1; the next-key flag 1, the reopened word guessed
2, not learned 2, the cap 1, the learned prefix 0, a commit without a word 1, the tail left out
2, changes waiting 1, a key ending the run 1.

Result: as predicted, each in the test named for it: 1; then 1, 1, 1; then 1, 2, 2, 1, 0, 1, 2,
1, 1.

The copy had no C call for the changes: `pull_changes` was Rust only, which the dead-code
warnings showed. `EnginePullChanges` (`BambooEngine::pull_changes_text`) now returns them, one
per line, `after`, the old words and the new ones separated by tabs, the words by spaces, in the
field's charset; a run holds letters only, so neither separator can occur in a word. Prediction,
before running: one test, which compares the text with `pull_changes` of a twin engine fed the
same keys, in VIQR; the text left in Unicode, 1 red; `after` left out, 1 (the same test).

Result: 1 and 1, after two runs that showed nothing because the defects were wrong, not the code.
The first left only the old words in Unicode, which are plain letters and the same in any charset;
the second did not apply once `cargo fmt` had split the line (the script reports whether the file
changed). Fixed, each defect fails the test. The copy builds: 19 of 19 `ctest`, 154 of 154 `cargo
test --release`. Two dead-code warnings are left, for the calls the C++ side still lacks: attaching
Đoán dấu to an engine with the table and personal dictionary every field shares (`set_diacritics`),
and marking a field private (`set_private`). Where Ngó Sen keeps those files and settings is the
front end's choice, so they wait for the binding in step 7.

## 2026-11-24 · VietTelex's 2 MB model on the same test files

Question: VietTelex (github.com/ptrinh/viettelex, MIT) ships Thêm dấu from a syllable model of
1,991,768 bytes, `vnlm.bin`, built from much the same corpora (Wikimedia, OpenSubtitles, FineWeb-2
forum pages, Tatoeba), against 22,650,872 bytes for the small table. Its own figures are on its
own test sets, so they say nothing here. How far behind is it on the frozen `wiki`, `subs` and
`forum` files?

Setup: VietTelex at commit `a150d25`, its `vnlm.bin` (sha256 `b4bd837f…2ae1`), `vnlexicon.bin` and
`enlexicon.bin` from `iOS/Keyboard/Resources`, restored by its own C++ port
(`windows/engine/src/add_tones.cpp`, default `Params`: second-order Viterbi and the curated pairs
on, no personal model), driven by `scripts/viettelex_restore.cpp`. The model is used to measure
only; nothing of it enters a table. `research.external strip` writes each test sentence lowercased
without marks, punctuation and spacing kept; `research.external score` counts the same words as
`research.evaluate` (every word token, `hoà`/`hòa` one spelling). Two inputs: whole sentences,
which is how Thêm dấu is used and lets it see across commas, and one run per line (`--runs`), the
context `research.evaluate` gives a table. The test files were lost with `/tmp` and rebuilt with
`research.fetch_wiki`, `research.fetch_subs` and `research.fetch_fineweb forum 1`, `2`, `3` (the
forum file is the first 4,000 lines of the three). Not measured: `chat`, whose source file is not
on this machine, and the personal dictionary, which VietTelex's static restore does not have.

Checks that the instruments see what they should, before the measurement:

- The driver restores VietTelex's own fixture (`iOS/KeyboardTests/Fixtures/add-tones.txt`) exactly:
  69 of 69 lines, all 69 changed from their input.
- The rebuilt files are the frozen ones only if the small table (release `table-small-v1`) scores
  what `docs/TABLES.md` records. Prediction: `wiki` 4,000 sentences, 73,604 words, 96.03%; `subs`
  4,000, 31,845, 95.73%; `forum` 4,000, 92,220, 93.26%. If a count or a figure differs, the files
  are not the frozen ones and the comparison below is on new files, to be said so.
- `research.external score` on the stripped input itself must give the share of words that carry
  no mark, and on the test file itself 100%.

Prediction, before running. VietTelex reports 93.36% on its Wikimedia dev set, 94.63% on its
OpenSubtitles test set and 93.32% on its FineWeb test set, but counts only syllables of its own
lexicon in filtered sentences; here every word counts, names and English included. So lower than
its own figures: whole sentences `wiki` 91.5%, `subs` 93.5%, `forum` 91.5%, each within 1.5 points;
behind the small table by about 4.5, 2.2 and 1.8 points. One run per line: within 0.3 points of
whole sentences, below it.

Result. The checks held: the small table scored 96.03%, 95.73% and 93.26% on 73,604, 31,845 and
92,220 words, so the rebuilt files are the frozen ones; the stripped input scored 20.03%, 15.94%
and 16.46%, and each test file against itself 100%. One line of `subs` holds a stray combining
mark after a word; stripped, it joined that word into a marked one and the sentence lost a token,
so `strip` now writes a space for such a mark and `score` aligns words only (a test covers it).
The figures below are from the run after that fix; `wiki` and `forum` did not move.

| | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| Small table, 22.65 MB | 96.03% | 95.73% | 93.26% |
| VietTelex, 1.99 MB, whole sentences | 92.94% | 94.30% | 89.54% |
| VietTelex, one run per line | 92.98% | 94.39% | 89.61% |
| Behind the small table (whole sentences) | 3.09 | 1.43 | 3.72 |
| Sentences all right: small table / VietTelex | 68.12% / 50.70% | 76.55% / 70.80% | 46.67% / 31.72% |
| Unmarked words changed: small table / VietTelex (runs) | 3.18% / 5.85% | 3.37% / 4.53% | 6.92% / 11.88% |

Against the prediction: `wiki` (91.5%) and `subs` (93.5%) hit, both higher than predicted, by 1.4
and 0.8; `forum` (91.5%) missed, 2.0 lower. The order of the gaps was wrong: predicted largest on
`wiki` and smallest on `forum`, it is largest on `forum` and smallest on `subs`. One run per line
is within 0.3 points as predicted, but above whole sentences, not below.

Conclusion: at a twelfth of the size VietTelex is 1.4 points behind on subtitles and 3 to 4 behind
on Wikipedia and forum text, where it leaves one sentence in two (`wiki`) and two in three
(`forum`) with a wrong word. Half of its loss on `forum` is unmarked words it adds marks to (11.88%
of them, against 6.92%): its lexicon holds Vietnamese syllables only, and forum text is full of
English and abbreviations. This compares two whole systems (model, lexicon, decoder and curated
pairs), not two table sizes: it does not say what the small table would score pruned to 2 MB,
which needs the trained model, not rebuilt here. Seeing context across commas did not help it.

## 2026-11-24 · How small can the table go?

Question: the small table is 22.65 MB because that size was chosen from count-pruned version 1
files; weighted pruning and the version 2 format came later and nobody looked below it again.
VietTelex's whole model is 1.99 MB ("VietTelex's 2 MB model on the same test files"). What does
the table lose at each size down to that, and is there a size well under 22.65 MB that loses
little?

Setup: the stored model (`data-store/model.npz`, trained as in `docs/TABLES.md`; the first draft
of this entry said it would be trained again, which was not needed), then `research.prune MODEL.npz OUT
--bytes N --min-plain 1000` for N = 22650896, 16, 11, 8, 6, 4, 3 MB (N × 1,000,000) and 1991768,
VietTelex's size. Scored with `research.evaluate` on the frozen `wiki`, `subs` and `forum` files,
the same copies as in the VietTelex entry. Format and scoring unchanged, so this moves one thing:
how many n-grams are kept. Not measured: `chat` and the personal dictionary (the chat file is not
on this machine); the sizes that hold up here still need that run before one is shipped.

Check that the stored model is the one the tables were built from: the table pruned to
22,650,896 bytes is byte for byte the released one (sha256 `295e88c0…1ba9`). If it is not, it
must at least score 96.03%, 95.73% and 93.26%; anything else and the sweep is on a different
model, to be said so.

Prediction, before running. From 14.4 MB to 22.65 MB the version 2 table gained 0.43, 0.37 and
0.57 points ("A denser table file"), about 0.65, 0.55 and 0.85 per doubling, and each halving
should cost more than the one before. Each figure within 0.5 points:

| Size | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| 22.65 MB | 96.03% | 95.73% | 93.26% |
| 16 MB | 95.75% | 95.50% | 92.85% |
| 11 MB | 95.30% | 95.15% | 92.30% |
| 8 MB | 94.85% | 94.80% | 91.80% |
| 6 MB | 94.40% | 94.45% | 91.30% |
| 4 MB | 93.60% | 93.90% | 90.50% |
| 3 MB | 93.00% | 93.40% | 89.80% |
| 1.99 MB | 92.00% | 92.70% | 88.80% |

So at VietTelex's size the table is expected to lose to VietTelex (92.94%, 94.30%, 89.54%) on
all three sets: it spends 6 bytes on an n-gram and 4 more on a bigram, where VietTelex's
quantized scores take a little over 2. If that holds, going far below 22.65 MB is a question of
the file format before it is one of pruning.

Result. The table pruned to 22,650,896 bytes is byte for byte the released one, so the model is the
one the tables were built from.

| Size | n-grams (bigrams + trigrams) | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- | --- |
| 22.65 MB | 912,919 + 2,052,941 | 96.03% | 95.73% | 93.26% |
| 16 MB | 676,165 + 1,339,049 | 95.66% | 95.41% | 92.83% |
| 11 MB | 482,970 + 827,707 | 95.26% | 95.09% | 92.34% |
| 8 MB | 357,780 + 536,357 | 94.76% | 94.82% | 91.88% |
| 6 MB | 268,362 + 352,053 | 94.19% | 94.50% | 91.27% |
| 4 MB | 171,310 + 180,473 | 93.49% | 93.91% | 90.45% |
| 3 MB | 117,962 + 102,720 | 92.80% | 93.33% | 89.81% |
| 1.99 MB | 57,933 + 34,730 | 91.32% | 92.04% | 88.13% |

Against the prediction: every size from 16 MB to 3 MB is within 0.21 points, inside the 0.5
allowed. At 1.99 MB all three miss by 0.66 to 0.68, lower than predicted: the words, their counts
and the candidate lists take about 1.2 MB whatever the size, so only 92,663 n-grams are left. As
predicted, the table then loses to VietTelex on every set (92.94%, 94.30%, 89.54%), by 1.6, 2.3
and 1.4 points; VietTelex keeps 862,285 n-grams in the same bytes. Each halving costs more than
the one before: 0.4 to 0.5 points from 22.65 to 11 MB, about 1.1 from 6 to 3 MB.

Conclusion: no size below 22.65 MB is free in this format, and far below it the format is the
limit, not the pruning.

## 2026-11-24 · Counts in one byte

Question: a version 2 file spends 6 bytes on a trigram (a 16-bit id, a 32-bit count) and 10 on a
bigram (the same, and a 32-bit offset to its trigrams); zstd shrinks the small table from 22.65 MB
to 8.06 MB, so most of that is slack. VietTelex stores a score in 4 to 6 bits. If each count were a
one-byte code, and the trigram offsets one byte per bigram with a full offset every 32 bigrams,
the same n-grams would take about half the file. Does restore still pick the same words?

Setup: `research.quant TABLE BITS TESTS`, on the released small table: counts of bigrams and
trigrams rounded in the log domain to 2^BITS levels between 1 and the largest count, word counts
left exact, scored with `research.evaluate` on the frozen files. The leftover of a context is one
minus the share of its count that its kept trigrams cover, so rounded counts can push an almost
covered context to the floor or away from it; `--keep-leftover` keeps the leftover the exact counts
gave, rounded to 256 levels, as a file with one more byte per bigram would. `dense_bytes` sizes the
layout above from the table's own numbers of bigrams and trigrams. No file is written yet: this
only says whether the rounding is safe and what it would save.

Check: BITS 0 leaves the counts exact and must score 96.03%, 95.73% and 93.26%.

Prediction, before running. Size of the small table's n-grams in the dense layout: about 11 MB,
half of 22.65 MB. A step at 8 bits is about 0.07 in log score, small next to the backoff (0.92), so
8 bits with the leftover kept: within 0.05 points of exact on every set. 8 bits with the leftover
from rounded counts: 0.1 to 0.5 points lower. 6 bits (step 0.29), leftover kept: 0.05 to 0.3 lower.
4 bits (step 1.2): 0.5 to 2 lower.

Result. BITS 0 scored 96.03%, 95.73% and 93.26%, as it must.

| Counts | Leftover | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- | --- |
| exact | from the counts | 96.03% | 95.73% | 93.26% |
| 8 bits | kept | 96.02% | 95.72% | 93.25% |
| 8 bits | from the rounded counts | 96.04% | 95.72% | 93.24% |
| 6 bits | kept | 96.01% | 95.73% | 93.25% |
| 4 bits | kept | 95.90% | 95.56% | 93.15% |

Against the prediction: 8 bits with the leftover kept hit (within 0.01). 8 bits with the leftover
from the rounded counts missed, the right way: no loss, not 0.1 to 0.5, so the leftover needs no
byte of its own. 6 bits missed the same way: within 0.02, below the predicted 0.05 to 0.3. 4 bits
missed: 0.10 to 0.17 lower, not 0.5 to 2. The dense layout holds the small table's n-grams in
11.13 MB, as predicted (about 11 MB).

Conclusion: restore needs the order of the counts, not their value; one byte per count is free.
Not tried: 6 or 4 bits with the leftover from the rounded counts, and bit-packed codes or ids, which
would save under a fifth more and cost a slower lookup.

## 2026-11-24 · Where accuracy stops rising, and what fits under 50 MB

Question: the owner's target changed from the smallest file to the most accurate one that can be
brought under 50 MB. How large must a table be before more n-grams stop helping, and how close to
that does a 30 MB or a 50 MB file come once counts take one byte ("Counts in one byte")?

Setup: `research.prune --bytes` at 130958840 (the large table), 260 MB and 520 MB, and the
unpruned model with `research.evaluate MODEL.npz`, all on the frozen `wiki`, `subs` and `forum`
files. For the dense layout, version 2 tables of 56, 62 and 68 MB (about 30 MB dense) and of 100,
110 and 120 MB (about 50 MB dense), each scored exact (`research.quant TABLE 0`) and with counts
rounded to 8 bits and the leftover kept (`research.quant TABLE 8 --keep-leftover`), which prints
the dense size. The model is the stored one (`data-store/model.npz`), not retrained: the entry
"How small can the table go?" says the corpora were fetched again, which was started and stopped
once the stored model was found. The stored test files are byte for byte the rebuilt ones.

Prediction, before reading any of these runs. Larger tables: 130.96 MB scores 97.15%, 96.59% and
94.30% as recorded; 260 MB adds 0.2 to 0.4 points on `wiki` and `forum`; 520 MB adds under 0.2
more; the unpruned model is within 0.2 of 520 MB, and may be lower on `subs` or `forum`, as the
unpruned count model was on chat. So accuracy stops rising between 260 MB and 520 MB. Dense: a
30 MB file holds the n-grams of a 60 MB version 2 table and scores about 96.65% on `wiki`, 96.2% on
`subs` and 93.85% on `forum`; a 50 MB file those of about 110 MB and scores about 97.05%, 96.5% and
94.2%, within 0.15 of the large table, each within 0.2 points.

Result. Version 2 tables and the unpruned model:

| File | n-grams (bigrams + trigrams) | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- | --- |
| 130.96 MB | 4,210,961 + 14,607,528 | 97.15% | 96.59% | 94.30% |
| 260 MB | 6,482,066 + 32,329,213 | 97.34% | 96.77% | 94.31% |
| 444.5 MB (every n-gram of the table's words) | 7,764,801 + 60,948,861 | 97.40% | 96.75% | 94.12% |
| unpruned model, 592,161 words | 16,110,696 + 78,578,293 | 97.52% | 96.83% | 94.27% |

`--bytes 520000000` asked for more than there is: with the 40,801 words `--min-plain 1000` keeps,
every n-gram fits in 444.5 MB. Dense layout, counts rounded to 8 bits with the leftover from the
rounded counts scored on the small table only; here exact counts and 8 bits with the leftover kept
were scored and differ by at most 0.02 points, so one figure is given:

| Dense file | Same n-grams in version 2 | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- | --- |
| 26.90 MB | 56 MB | 96.77% | 96.29% | 94.03% |
| 29.75 MB | 62 MB | 96.82% | 96.29% | 94.05% |
| 32.60 MB | 68 MB | 96.88% | 96.36% | 94.07% |
| 47.72 MB | 100 MB | 97.07% | 96.55% | 94.27% |
| 52.45 MB | 110 MB | 97.07% | 96.61% | 94.26% |
| 57.18 MB | 120 MB | 97.10% | 96.59% | 94.28% |

Against the prediction: 130.96 MB as recorded. 260 MB adds 0.19 on `wiki`, just under the
predicted 0.2 to 0.4, and 0.01 on `forum`: missed. The largest table adds 0.06 on `wiki` and loses
0.19 on `forum`; the unpruned model is within 0.2 of it and not lower. "Stops rising between 260
and 520 MB" was wrong in shape: `forum` stops at 131 MB and is lower with every n-gram kept, `wiki`
creeps up to the unpruned model. The dense figures hit: 29.75 MB gives 96.82%, 96.29% and 94.05%
(predicted 96.65%, 96.2%, 93.85%) and 47.72 MB gives 97.07%, 96.55% and 94.27% (predicted 97.05%,
96.5%, 94.2%).

Conclusion: the ceiling is about 97.5%, 96.8% and 94.3%. A dense file of 47.72 MB is 0.45, 0.28
and 0.00 points under it and 1.04, 0.82 and 1.01 above the small table; one of 29.75 MB takes
three quarters of that gain. Past 48 MB ten more megabytes buy a few hundredths. These are sizes
computed for a layout no file uses yet: the next step is version 3 of the format in
`research.table` and the crate, checked against these figures. Not measured: `chat`, where the
small and large tables were level with the personal dictionary, so the gain may be on edited text
only.

## 2026-11-25 · Format version 3: one byte per count, under 50 MB

Question: "Where accuracy stops rising" sized a dense layout without writing it. Does a real file
in that layout, read by `research.table` and by the crate, score what was computed, and what does
the largest table under 50 MB (50,000,000 bytes) score?

Setup: format version 3 (layout in `research/table.py`): per bigram a 16-bit id, a count code and a
leftover code; per trigram a 16-bit id and a count code; the trigrams of a bigram are found from
one length byte per bigram and a full offset every 32 bigrams. A count is the nearest of 256 levels
spaced evenly in log between 1 and the largest count. The leftover of each context is taken from
the exact counts when the file is written, and stored: a byte per bigram and a float per word.
Tables from the stored model with `research.prune --min-plain 1000`, scored with
`research.evaluate` on the frozen `wiki`, `subs` and `forum` files. The crate is compared with
`research.table` on every run of the three files (`research.crosscheck`, then the `restore`
example), and timed with the `latency` example in runs of 50 and 200 against `main` reading a
version 2 table of the same n-grams, alternately, twice each; the learned text is the first 500
lines of the frozen `subs` file.

Check that the format is what changed: `--entries 2965860` keeps the n-grams of the released small
table (912,919 bigrams and 2,052,941 trigrams), which scored 96.03%, 95.73% and 93.26% in version 2.

Prediction, before writing any real table:

- the small table's n-grams: 912,919 + 2,052,941 again, a file of 12.2 to 12.6 MB (11.13 MB
  computed, plus a leftover byte per bigram and the per-word floats), each set within 0.03 points
  of version 2;
- `--bytes 50000000`: a file between 49.5 and 50.0 MB, about 3.2 million bigrams and 10.6 million
  trigrams, scoring 97.05%, 96.55% and 94.25%, each within 0.1;
- `--bytes 30000000`: 96.80%, 96.30% and 94.05%, each within 0.1;
- the crate restores every run of the three files like `research.table`, on both tables;
- timing on the 50 MB table: p50 per key up to 30% above version 2 with the same n-grams, since a
  trigram lookup now adds up to 31 lengths; p99 per key under 3 ms in runs of 50 and of 200;
  opening takes under half the time, since version 2 summed every trigram count on opening.

Result. Tables, scored by `research.evaluate`:

| Table | File | n-grams (bigrams + trigrams) | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- | --- | --- |
| `--entries 2965860` | 12,374,504 bytes | 912,919 + 2,052,941 | 96.03% | 95.75% | 93.26% |
| `--bytes 30000000` | 29,821,584 bytes | 1,982,506 + 6,038,540 | 96.75% | 96.32% | 94.07% |
| `--bytes 50000000` | 49,687,280 bytes | 3,184,296 + 10,604,400 | 97.04% | 96.55% | 94.26% |

The crate against `research.table`, on the 11,765 runs of `wiki`, the 5,460 of `subs` and the
10,179 of `forum`: no run differs, on any of the three tables. That the comparison can see a
difference: the 50 MB and the 30 MB table restore 494 `wiki` runs differently.

Timing, `latency` example, release build, Xeon E5-2696 v4, load average 5.3 at the start and 2.4 at
the end (other jobs ran); 197,650 keys in runs of 50 and 197,600 in runs of 200, from the runs of
the three files. `main` read a version 2 table of the same 3,184,296 + 10,604,400 n-grams
(96.67 MB), the branch the 49.69 MB table; rounds 1 and 2:

| | `main`, version 2 | branch, version 3 |
| --- | --- | --- |
| open | 133.0, 135.8 ms | 43.9, 44.5 ms |
| resident after typing | 117.0, 116.8 MB | 56.4, 56.4 MB |
| p50 per key, runs of 50 | 0.287, 0.285 ms | 0.291, 0.277 ms |
| p99 per key, runs of 50 | 1.950, 1.931 ms | 1.987, 1.903 ms |
| p50 per key, runs of 200 | 0.311, 0.294 ms | 0.320, 0.299 ms |
| p99 per key, runs of 200 | 1.952, 1.869 ms | 2.021, 1.909 ms |
| largest key | 12.2 ms | 12.4 ms |

The two versions do not type the same text (the hashes of what was shown differ), as rounded
counts allow; each is the same in both of its rounds. The 12.37 MB table opens in 16.7 ms, holds
18.6 MB after typing and has p99 1.646 ms per key in runs of 50 (one round).

Against the prediction: the small table's n-grams are the same and the file is 12.37 MB, as
predicted; `wiki` and `forum` are equal to version 2 and `subs` is 0.02 higher. The 50 MB file is
49.69 MB with 3.18 million bigrams and 10.60 million trigrams and scores within 0.01 of the
prediction on every set. The 30 MB file is within 0.05. The crate restores every run alike. Timing
missed the right way on p50: no slowdown outside the spread between rounds, not up to 30%; p99
stays near 2 ms, under 3 ms; opening takes a third of the time, as predicted (under half).

Conclusion: version 3 holds the same n-grams in about half the file with no loss in accuracy or
speed, and a table under 50 MB scores 97.04%, 96.55% and 94.26%: 1.01, 0.82 and 1.00 points above
the released small table, and 0.11, 0.04 and 0.04 under the 130.96 MB table of version 2. Not
measured: `chat` with and without the personal dictionary on either version 3 table; the first key
after opening; and a download compressed with zstd, which took the version 2 small table from
22.65 MB to 8.06 MB.

## 2026-11-25 · The two version 3 tables on Messenger chat

Question: the 49.69 MB table is about one point above the 12.37 MB one on edited prose. Is it also
ahead on chat, alone and with the personal dictionary? That decides which one is the default.

Setup: a new chat set, not comparable with the earlier ones (those were prompts typed to a coding
assistant): the maintainer's own messages from a Messenger export, other senders left out, links
and repeated messages removed, the latest 20,000 kept; `research.chat_testset` makes 18,553
sentences and 126,027 words of them. Kept in RAM and deleted after the run. Both tables from
"Format version 3: one byte per count, under 50 MB", scored with
`research.personal TABLE CHAT 0 auto`: weight 0 is the table alone, `auto` the personal dictionary
learned from the other four fifths, 5-fold.

Check that the personal counts are applied: `auto` must differ from weight 0 on both tables.

Prediction, before any run on this set. Messages to people are less technical and more colloquial
than the prompts, with more words the table lacks, so the table alone scores lower than the 90.6%
of the earlier chat set: small 86% to 90%. The large table is 0.1 to 0.5 points above the small one
alone. The personal dictionary adds 2 to 4 points to each, and with it the two tables are within
0.3 points of each other, as on the earlier chat set (92.91% and 92.78%).

Result, 123,071 words scored:

| | Small, 12.37 MB | Large, 49.69 MB |
| --- | --- | --- |
| table alone (weight 0) | 82.94% | 83.95% |
| with the personal dictionary (`auto`) | 89.24% | 88.49% |

The check passed: `auto` differs from weight 0 by 6.30 and 4.54 points.

Against the prediction: missed on every count. The table alone is 3 points under the predicted
range (82.94%, not 86% to 90%). The large table is 1.01 above the small one alone, not 0.1 to 0.5.
The personal dictionary adds 6.30 and 4.54 points, not 2 to 4. With it the small table is ahead by
0.75, outside the 0.3 predicted.

Conclusion: on chat the default stays the small table. The large one is better only for a user
with no personal dictionary yet; once the dictionary has learned, the small table gets more words
right in a quarter of the file. The personal dictionary matters more here than table size: 6
points against 1. Not tried: why the large table gains less (a fixed weight instead of `auto`, or a
weight scaled to the number of n-grams kept), how many messages it takes for the small table to
pass the large one (`--fractions`), and other writers.

## 2026-11-25 · The same table file on every machine

Question: CI rebuilt the test table and got a file that differs from the committed one in one byte
of a count level. The levels come from `exp`, whose last bit depends on the CPU. With every stored
float rounded to single precision, do the two tables of "Format version 3" still score the same?

Setup: `research.table` rounds the count levels, the leftover levels and the per-word leftovers to
single precision before writing. The two tables rebuilt with the same commands and scored with
`research.evaluate` on the frozen files.

No prediction was written before this run, so it proves little beyond the figures themselves. The
expectation was the same n-grams and file sizes, and scores that move only where a word was a near
tie.

Result: the same n-grams and sizes (12,374,504 and 49,687,280 bytes).

| Table | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| 12.37 MB, before → after | 96.03% → 96.03% | 95.75% → 95.74% | 93.26% → 93.27% |
| 49.69 MB, before → after | 97.04% → 97.04% | 96.55% → 96.55% | 94.26% → 94.26% |

Two figures of the small table move by 0.01. The tables in the docs are the rebuilt ones from here on. Not checked: that a
machine with another CPU writes the same real tables byte for byte; CI checks it for the two test
tables only.

The chat set was built again from the same export and the rebuilt tables scored on it, with the
same commands: alone 82.92% and 83.93%, with the personal dictionary 89.24% and 88.49%. The docs
give these.

## 2026-11-26 · Typos the corpus has, taken out of the table

Question: both version 3 tables restore `khogn` as `khôgn`. The corpus has that Telex typo 100
times, so the table knows `khogn` and the syllable fix never sees it: the example the docs give for
the fix does not work on the released tables. Does leaving out rare spellings that are typos of a
common syllable let the fix reach them, without costing accuracy on clean text?

Setup: `table.drop_typos` with `--drop-typos 1000` leaves out a spelling seen fewer than 1,000 times
that is no syllable (`text.is_syllable`: an onset, one to three vowels and a coda) and whose plain
form is one edit from a plain form whose best spelling is a syllable seen at least 10,000 times. A
plain form left with no spelling then restores as typed and is a fix target. A filter on the
syllable shape alone was looked at first and set aside: on the small table it drops 16,075 spellings,
among them loanwords people write (`sôcôla`, `milivôn`). The one-edit condition narrows that to 4,301
on the small table (`arất`, `bcủa`, `nămm`, `đamg`, `phònng`, but also `kơho` and `carô`).
Tables from the stored model with the commands of "Format version 3: one byte per count, under
50 MB" plus `--drop-typos 1000`: `research.prune MODEL --entries 2965860 --min-plain 1000` and
`--bytes 50000000 --min-plain 1000`. Scored with `research.evaluate` and `research.typo` (margin 4,
the crate's `FIX_MARGIN`) on the frozen `wiki`, `subs` and `forum` files, against the released
version 3 tables, which are scored with `research.typo` here for the first time.

Check that the filter is applied: `prune` reports the spellings dropped, and `khogn` is missing from
the new tables' plain forms while `không` is still there.

Prediction, before building either table:

- 4,000 to 12,000 spellings dropped from the model (the model keeps spellings seen 5 times or more,
  more than either table);
- the small table's file within 0.1 MB of 12.37 MB with the same number of n-grams;
- `research.evaluate` within 0.02 points of the released tables on each set, on both tables;
- `research.typo`, margin 4: the share of typos landing on a known form falls by 0.5 to 2 points on
  each set, typos fixed right rise by 0.3 to 1.5 points, fixes stay at least 98.5% right, and
  clean words changed stay at or under 0.01%;
- the crate fixes `toi khogn biet` to `tôi không biết` at the end of the run on the new small table.

The check passed: `prune` dropped 4,301 spellings for each table, `khogn` is no longer a plain
form of either new table, and `khong` keeps its spellings. The released tables, scored again here,
give the documented `research.evaluate` figures, so the numbers below compare like with like.

Result. `research.evaluate`:

| Table | File | n-grams | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- | --- | --- |
| small, released | 12,374,504 bytes | 912,919 + 2,052,941 | 96.03% | 95.74% | 93.27% |
| small, `--drop-typos 1000` | 12,161,520 bytes | 908,736 + 2,057,124 | 96.03% | 95.75% | 93.26% |
| large, released | 49,687,280 bytes | 3,184,296 + 10,604,400 | 97.04% | 96.55% | 94.26% |
| large, `--drop-typos 1000` | 49,684,536 bytes | 3,168,771 + 10,697,980 | 97.04% | 96.55% | 94.26% |

`research.typo` at margin 4, the same typos on both tables of a size (11,248 on `wiki`, 5,364 on
`subs`, 9,891 on `forum`). Fixed right is given as a share of all typos, since the typos that land
on a known form, which are left out of the scored ones, are what the filter changes:

| Table, set | Landed on a known form | Fixed right, of all typos | Right, of fixes | Clean words changed |
| --- | --- | --- | --- | --- |
| small, `wiki` | 42.41% → 33.99% | 25.97% → 29.38% | 99.4% → 99.2% | 0.005% → 0.007% |
| small, `subs` | 49.96% → 40.14% | 24.87% → 29.93% | 99.3% → 99.1% | 0.009% → 0.009% |
| small, `forum` | 45.46% → 36.70% | 23.78% → 27.91% | 98.7% → 98.3% | 0.011% → 0.012% |
| large, `wiki` | 42.41% → 33.99% | 25.92% → 29.44% | 99.5% → 99.4% | 0.011% → 0.012% |
| large, `subs` | 49.96% → 40.14% | 25.17% → 30.29% | 99.0% → 99.0% | 0.009% → 0.009% |
| large, `forum` | 45.46% → 36.70% | 24.82% → 29.18% | 98.4% → 98.5% | 0.014% → 0.017% |

The crate (`Typing::fix` on the new small table) fixes `khogn` in `toi khogn biet` to `khong`, then
marked `không`, by a margin of 14.8; on the released table it restores `khôgn`. `khogn` typed alone
is not fixed (margin −0.9): with no context the fix is not sure enough.

Against the prediction: 4,301 spellings dropped, at the low end of 4,000 to 12,000: the model keeps
no typo of this kind that the tables leave out. The small file is 0.21 MB smaller, outside the
0.1 MB predicted: 5,728 fewer words, and the n-grams through them. Accuracy on clean text moved by at
most 0.01 points, as predicted. The typo figures missed by far, the right way: typos landing on a
known form fell by 8.4 to 9.8 points (0.5 to 2 predicted), and typos fixed right rose by 3.4 to 5.1
points of all typos (0.3 to 1.5 predicted). Corpus typos are the very typos people make, so the few
thousand left out took a fifth of the typos that landed on a known form. Fixes right missed on `forum` with the
small table: 98.3%, under the 98.5% predicted, still above the 98% that "Fixing syllables the table
does not know" asked of auto-fixing. Clean words changed stayed at or under 0.012%, against 0.01%
predicted: missed on `forum` by 0.002 on the small table and 0.007 on the large one, at one to
three words in 92,220.

Conclusion: leaving out these spellings costs nothing measurable on clean text and lets the fix
put right about 4 more typos in 100. Not measured: the chat set (with and
without the personal dictionary) and the hand-labelled real typos of "Fixing unknown syllables on
real typos", both of which need the writer's messages; the released tables stay as they are until
chat is measured.

## 2026-11-26 · Lower fix margins, decided when the word ends

Question: Ngó Sen may offer the syllable fix at three levels, each a margin passed to
`Run::fixing`, and will ship only levels with a measured precision. On the released small table, how
do the share of fixes that are right and the typos fixed change at margins 3, 2 and 1, decided when
the word ends as the crate does?

Setup: `research.typo --typing` on the released 12.37 MB table, frozen `wiki`, `subs` and `forum`
files, the typo model and seed of the earlier entries; the script prints every margin of
`MARGINS`. "Fixing unknown syllables in the crate, decided when a word ends" showed the crate makes
the same decisions as `research.typo --typing`. Fixed right is also given as a share of all typos.

Check that the margins are applied: the figures must change from one margin to the next, and margin
4 must be near that entry's figures (23.2–24.8% of scored typos fixed right, 98.0–99.5% right).

Prediction, before the run:

- margin 4: 22–26% of scored typos fixed right, 98.0–99.5% of fixes right on each set;
- margin 3: 96.5–98.5% right, 2–4 points more typos fixed;
- margin 2: 94–97% right; margin 1: 90–95% right;
- clean words changed at most 0.03% at margin 1 on every set.

Result, released small table, decided when the word ends (fixes right / typos fixed right, of the
scored typos and of all typos / clean words changed). The forum file has sha256 prefix
f3340b657361c8d7.

| Margin | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| 4 | 99.5% / 24.0%, 13.8% / 0.005% | 98.7% / 24.7%, 12.4% / 0.006% | 98.0% / 21.5%, 11.7% / 0.004% |
| 3 | 98.9% / 28.5%, 16.4% / 0.007% | 97.0% / 31.2%, 15.6% / 0.009% | 96.7% / 27.0%, 14.7% / 0.007% |
| 2 | 97.4% / 33.0%, 19.0% / 0.012% | 95.1% / 37.6%, 18.8% / 0.009% | 94.8% / 31.9%, 17.4% / 0.009% |
| 1 | 95.0% / 37.1%, 21.4% / 0.016% | 92.1% / 43.7%, 21.9% / 0.013% | 90.4% / 38.1%, 20.8% / 0.013% |

The check passed: every figure moves from one margin to the next, and margin 4 is within the
earlier entry's range (24.0%, 24.7% and 21.5% fixed right; 98.0% to 99.5% right).

Against the prediction: margin 4 hit on both counts. Margin 3 is right 96.7% to 98.9% of the time:
`subs` and `forum` in the predicted 96.5% to 98.5%, `wiki` above it; it fixes 4.5 to 6.5 points
more of the scored typos, not 2 to 4. Margin 2 is right 94.8% to 97.4%: `wiki` above the predicted
94% to 97%. Margin 1 hit (90.4% to 95.0%), as did clean words changed (at most 0.016%).

Conclusion: each step down from 4 buys about 3 more typos fixed in 100, and costs 1 to 2 points
of the fixes being right at margin 3, 3 to 4 at margin 2 and 5 to 8 at margin 1, where one fix in
ten is wrong on `forum`. A setting with three levels can stand on margins 4, 3 and 2: at worst
98.0%, 96.7% and 94.8% right. These are synthetic typos, and decided only by the words before; the
writer's chat and real typos are not measured, and on real typos at margin 4 ("Fixing unknown
syllables on real typos") fixes were too few to give a share.

## 2026-11-27 · Fixing a word by the keys it was typed with

Question: the syllable fix only reaches a word shown as unmarked letters the table lacks, one
plain-letter edit from a known form. A slip while typing Telex marks is further than that: `nguoiwff`
(the tone key twice) and `nguwowpif` (an extra `p` beside `o`) come back from Ngó Sen's core as the
raw keys, three letters from `nguoi`; `mguoifw` and `bguoiwd` have a neighbouring key in place of a
letter or of the tone key; `nguooif` (`oo` for `ow`) comes out as `nguồi`, which the table has seen
67 times against 3,186,700 for `người`. If the candidates are instead the words that keys one or two
slips away would have typed, how many more slips are put right, and how many words typed right are
changed?

Setup: `research.telex_typo` on the released 12.37 MB table (sha256 prefix 318ec5e0), frozen `wiki`,
`subs` and `forum` files (sha256 prefixes 5ba7b049, b0f7d4eb, f3340b65), 4,000 lines each. Each word
is typed as Telex keys (`research.mixed_readings.telex_keys`, the tone key at the end, after its
vowel or after the last vowel) and read back through Ngó Sen's core at its default settings:
`scripts/ngosen_near.rs`, built against `bamboo-rs` of ngosen/ngosen at dc730ec2, with its
dictionary, English list and keep list. For a target the driver types every key string one slip
away, and two slips away when neither is a far key, an unrelated extra key or an unrelated missing
key, and gives the words the core shows for them. A candidate must have been seen 1,000 times. It is
scored by the trigram that ends at it, less a cost per slip: 1 unit for a neighbouring key, `oo` for
`ow`, two keys swapped, a key hit twice, an extra key beside its neighbour and one key of a doubled
pair left out; 2 for any other extra or missing key; 2.5 for any other key. The scale turns units
into the score's unit; scales 0, 2, 4 and 6 and margins 0 to 12 are all printed. The fix is decided
when the word ends, so only the words before it are context, and those are taken as typed right.
`--plain` types every word without marks instead; the words before are then what restore guesses.
`--rare 1000` also makes a target of a shown word the table has seen fewer than 1,000 times, kept at
its own score instead of the unknown word's.

One word per run gets a slip, in any word of two keys or more, known to the table or not. The share
of each kind is assumed, not measured: a neighbouring key 35%, two keys swapped 15%, an extra key
beside the one before or after 15%, a key left out 15%, a key hit twice 10%, a far key 5%, `oo` for
`ow` or back 5%; one mistyped word in ten gets a second slip onto a neighbouring key ("two"). The
candidates are drawn from the same kinds of slip, so the typos suit the fix, as in "Fixing syllables
the table does not know". A slip the core reads as the intended word anyway (`nguoifw`) is counted
and left out. "today" is the crate's fix on the same words, scored the same way.

Seen before this prediction: the driver's output for the five key strings above (after one slip or
two, `người` is among the words nearby for each; `mguoifw` also gives `mười` and `bguoiwd` gives
`bưởi`); the table's counts for the spellings of `nguoi`; one run on six made-up sentences, to see
that the script works; the driver takes 52 ms a word on one core (2,000 known forms, 6.1 keys on
average), about 3,400 key strings typed per word. No figure on the test files.

Checks. `--keys` after `mọi`: `mguoifw`, `bguoiwd`, `nguoiwff` and `nguwowpif` must each give
`người` at scales 0 and 2 with a margin of 4 or more; `nguooif` must give nothing without `--rare`
and `người` with `--rare 1000`. After `tháng`, `mguoifw` must give `mười` at scales 0 and 2: the
words before decide between two candidates. In `--plain`, "today" at margin 4 must be right 97% to
99.6% of the time, near the 98.0% to 99.5% of "Lower fix margins, decided when the word ends"; the
slips differ, so the share fixed is not comparable.

Prediction, before the run, the same on each set unless said.

- Slips the core reads as intended: 8% to 15% with marks typed.
- "today", marks typed, margin 4: 3% to 7% of the mistyped words fixed right; clean words changed at
  most 0.01%. With `--plain`: 9% to 14% fixed right.
- Nearby keys, marks typed, scale 0, margin 4: 30% to 45% fixed right, 96% to 99% of fixes right,
  clean words changed at most 0.02%. Scale 2, margin 4: 25% to 40% fixed right, 98% to 99.5% of
  fixes right, clean words changed at most 0.01%.
- By kind, scale 2, margin 4: a key hit twice, `oo` for `ow`, a neighbouring key, an extra key
  beside and two keys swapped each 35% to 50% fixed right; a key left out, a far key and two slips
  each 10% to 25%.
- `--plain`, scale 0, margin 4: 14% to 22% fixed right, more than "today" because a slip onto a mark
  key shows a marked word that "today" does not look at.
- `--rare 1000`, marks typed: 1 to 3 points more fixed right at the same scale and margin, and clean
  words changed 0.02% to 0.08% at scale 0, margin 4; it needs scale 4 or margin 8 to come under
  0.012%.

The fix is worth building if, with marks typed, some scale and margin on all three sets changes at
most 0.012% of the words typed right (the most the fix changes today, at margin 2), is right at
least 98% of the time and fixes right at least twice as many mistyped words as "today".

Result. The checks passed: after `mọi`, `mguoifw`, `bguoiwd`, `nguoiwff` and `nguwowpif` give
`người` by 9.4 at scale 0 and by 5.4 to 7.4 at scale 2; `nguooif` gives nothing without `--rare`
and `người` by 8.2 with `--rare 1000`; after `tháng`, `mguoifw` gives `mười` (6.4 and 2.4). "today"
in `--plain` at margin 4 is right 98.0% to 98.6% of the time.

Where the mistyped words went, marks typed (share of the scored ones). The script printed these
three counts only from a second run on; that run gave the same figures as the first in every other
line.

| | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| Read as the intended word, left out | 577 | 294 | 533 |
| Scored | 11,026 | 5,153 | 9,514 |
| Shows a word the table knows, so no target | 2,802 (25.4%) | 1,609 (31.2%) | 2,644 (27.8%) |
| Intended word among the candidates | 7,412 (67.2%) | 3,364 (65.3%) | 6,533 (68.7%) |
| Neither | 812 (7.4%) | 180 (3.5%) | 337 (3.5%) |

Marks typed, without `--rare` (mistyped words fixed right / fixes right / words typed right that
were changed, of 73,104, 31,746 and 91,991):

| | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| today, margin 4 | 5.3% / 98.5% / 0.007% | 5.2% / 96.0% / 0.006% | 4.3% / 95.6% / 0.004% |
| today, margin 2 | 6.6% / 94.8% / 0.015% | 7.3% / 92.1% / 0.009% | 6.3% / 92.7% / 0.007% |
| scale 0, margin 0 | 40.5% / 88.8% / 0.090% | 40.3% / 83.3% / 0.079% | 39.2% / 83.1% / 0.077% |
| scale 0, margin 4 | 21.4% / 98.9% / 0.007% | 20.5% / 98.9% / 0.013% | 20.3% / 98.3% / 0.005% |
| scale 2, margin 4 | 15.8% / 99.8% / 0.000% | 13.0% / 99.7% / 0.003% | 13.6% / 99.5% / 0.001% |
| scale 2, margin 2 | 22.5% / 99.4% / 0.004% | 23.7% / 98.9% / 0.009% | 22.1% / 98.8% / 0.002% |
| scale 4, margin 0 | 21.4% / 99.3% / 0.000% | 22.6% / 99.1% / 0.009% | 21.3% / 98.7% / 0.003% |

Fixed right by kind of slip, scale 2, margin 4:

| Kind | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| a key hit twice | 21.9% | 17.9% | 21.3% |
| an extra key beside | 20.0% | 21.5% | 17.3% |
| two keys swapped | 19.8% | 14.9% | 15.1% |
| a neighbouring key | 17.6% | 15.0% | 15.2% |
| `oo` for `ow` or back | 14.6% | 10.2% | 13.7% |
| two slips | 12.1% | 9.0% | 11.1% |
| a far key | 10.1% | 3.0% | 7.3% |
| a key left out | 5.5% | 2.4% | 3.3% |

`--plain` (11,304, 5,259 and 9,778 mistyped words scored; 42.0%, 51.1% and 45.6% of them show a word
the table knows, and 51.1%, 46.2% and 51.1% have the intended word among the candidates):

| | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| today, margin 4 | 11.5% / 98.6% / 0.007% | 11.1% / 98.0% / 0.006% | 11.8% / 98.2% / 0.003% |
| scale 0, margin 4 | 11.2% / 97.2% / 0.008% | 9.1% / 96.0% / 0.013% | 10.5% / 96.0% / 0.004% |
| scale 2, margin 2 | 13.3% / 98.1% / 0.007% | 13.1% / 97.3% / 0.009% | 13.6% / 97.6% / 0.001% |
| scale 2, margin 4 | 8.9% / 99.6% / 0.000% | 6.8% / 99.7% / 0.003% | 7.9% / 99.4% / 0.000% |

`--rare 1000`, marks typed (the intended word is then among the candidates for 8,385, 3,938 and
7,415 of the mistyped words):

| | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| scale 0, margin 4 | 24.3% / 98.7% / 0.015% | 23.9% / 98.5% / 0.038% | 22.9% / 98.2% / 0.025% |
| scale 2, margin 2 | 28.3% / 98.1% / 0.030% | 30.4% / 97.6% / 0.038% | 27.2% / 97.0% / 0.051% |
| scale 2, margin 4 | 20.0% / 99.7% / 0.010% | 17.9% / 98.8% / 0.016% | 17.0% / 98.8% / 0.018% |
| scale 2, margin 6 | 11.0% / 99.8% / 0.001% | 8.2% / 99.8% / 0.009% | 8.6% / 99.8% / 0.008% |
| scale 4, margin 4 | 12.9% / 99.1% / 0.008% | 10.8% / 98.9% / 0.009% | 10.4% / 98.3% / 0.017% |

Each run of the three files took 94 to 100 seconds on 44 copies of the driver.

Against the prediction: most of it missed, on the high side.

- Slips the core reads as intended: 5.0%, 5.4% and 5.3%, not 8% to 15%.
- "today" hit: 4.3% to 5.3% fixed right with marks typed, 11.1% to 11.8% with `--plain`, clean
  words changed at most 0.007%.
- Nearby keys, scale 0, margin 4: 20.3% to 21.4% fixed right, not 30% to 45%. Fixes right (98.3%
  to 98.9%) and clean words changed (at most 0.013%) hit. Scale 2, margin 4: 13.0% to 15.8%, not
  25% to 40%; fixes are right 99.5% to 99.8% of the time, at or above the predicted 98% to 99.5%.
- By kind: none of the five kinds predicted at 35% to 50% passes 22%. A key left out is at 2.4% to
  5.5%, not 10% to 25%; a far key and two slips reach 10% only on `wiki` and, for two slips, on
  `forum`.
- `--plain`, scale 0, margin 4: 9.1% to 11.2%, not 14% to 22%, and below "today" on every set. The
  reason given for expecting more was wrong: with no marks typed, about half of the slips land on a
  word the table knows, which neither fix touches.
- `--rare 1000`: 2.6 to 3.4 points more fixed right at scale 0, margin 4 (predicted 1 to 3) and 3.4
  to 4.9 more at scale 2. Clean words changed are 0.015% to 0.038% at scale 0, margin 4 (`wiki`
  below the predicted 0.02% to 0.08%). Scale 4 at margin 4 does not bring `forum` under 0.012%;
  scale 2 at margin 6 does, on every set.

Conclusion: with marks typed the fix meets the bar set before the run. At scale 2, margin 2 it puts
right 22.1% to 23.7% of the mistyped words, 4.2 to 5.1 times what the fix does today at margin 4;
its fixes are right 98.8% to 99.4% of the time and it changes at most 0.009% of the words typed
right. Scale 4, margin 0 does the same within a point. Both were picked after seeing these files,
and 0.009% on `subs` is 3 words where the bar is 4, so the pick wants a run on lines it has not
seen before anything is built on it.

What holds it back is the context, not the search: the intended word is among the candidates for
two mistyped words in three, and with no margin and no cost the words before pick it for only 40%
of the mistyped words. A quarter to a third of the slips show a word the table already knows and are
never looked at.
`--rare 1000` looks at some of those, but every rare word typed right then becomes a target too: at
a like share of clean words changed (scale 2, margin 6) it fixes 8.2% to 11.0%, less than half of
what scale 2, margin 2 does without it. A slip that lands on a real word (`nguooif` as `nguồi`)
needs a narrower rule than "rare", not measured here.

Typing without marks gains nothing: no scale and margin is right 98% of the time on `subs` while
fixing more than "today".

Limits. The slips are synthetic, drawn from the same seven kinds the candidates are made of, in
shares that were assumed; a writer's real slips are not measured. Only the words before are
context. Telex only. One word in `subs` is 0.003% of its clean words, so the shares of clean words
changed stand on a handful of words. The driver types about 3,400 key strings for each word, 52 ms
on one core: a fix in the input method needs another way to find the candidates.

## 2026-11-27 · The typed-keys fix on lines it was not picked on

Question: "Fixing a word by the keys it was typed with" picked scale 2 with margin 2, and scale 4
with margin 0, after seeing the frozen files, and its share of clean words changed stood on 3 words
in `subs`. Do the two settings still meet that entry's bar on held-out text they were not picked on?

Setup: the same script, table, driver and seed, marks typed, no `--rare`. Three files, none of them
read in that entry:

- `wiki-unseen`: the held-out Wikipedia sentences after the 4,000 of the test set, written by
  `research.wiki_rest`, which stops unless the first 4,000 it finds are `test/wiki` line for line;
  less the lines the frozen file also has. 9,170 lines, 167,878 words by `wc -w`, sha256 prefix
  df836b36f36f0f30.
- `forum-unseen`: lines 1,774 on of `forum-3` and all of `forum-4`, less 5 lines the frozen file
  also has. 2,742 lines, 67,483 words, sha256 prefix 250dbd7b904d002f.
- `social`: the 9,780 ViLexNorm comments as typed, 123,509 words, sha256 prefix 44fa1104f5ecadbe.
  Slang, abbreviations and the writers' own typos are words typed right here, so a change to one of
  them counts as a clean word changed even where it corrects a real typo.

There are no more subtitles to use: by the rule of `fetch_subs` on the same OPUS file (its first
4,000 usable held-out lines are `test/subs` line for line), 116 lines are left.

Seen before this prediction: the line and word counts above. The count of shared lines was checked
with the frozen forum file against itself (3,911 of 3,911 distinct lines found). Nothing from the
script on these files.

Prediction, before the run.

- `wiki-unseen`. "today", margin 4: 4.8% to 5.8% of the mistyped words fixed right, 97.5% to 99.2%
  of fixes right. Scale 2, margin 2: 21% to 24% fixed right, 99.0% to 99.7% of fixes right, at most
  0.008% of the words typed right changed. Scale 4, margin 0: 20% to 23%, 98.8% to 99.6%, at most
  0.005%.
- `forum-unseen`. "today", margin 4: 3.8% to 5.0% fixed right, 94.5% to 98.0% of fixes right. Scale
  2, margin 2: 20% to 24%, 98.2% to 99.3%, at most 0.008%. Scale 4, margin 0: 19.5% to 23%, 98.0%
  to 99.2%, at most 0.008%.
- `social`. Slips the core reads as intended: 4.5% to 6%. "today", margin 4: 2% to 4% fixed right,
  0.02% to 0.08% of the words as typed changed. Scale 2, margin 2: 12% to 18% fixed right, 96% to
  98.5% of fixes right, 0.03% to 0.15% of the words as typed changed.

The pick is confirmed if scale 2 with margin 2 meets the bar on `wiki-unseen` and on `forum-unseen`:
at most 0.012% of the words typed right changed, 98% of fixes right, twice what "today" fixes right
at margin 4. `social` has no bar: it shows what the fix costs on writing full of words the table
lacks.

Result (mistyped words fixed right / fixes right / words typed right that were changed, of 160,078,
66,249 and 118,316; 21,112, 6,955 and 14,043 mistyped words scored). The run took 159 seconds.

| | `wiki-unseen` | `forum-unseen` | `social` |
| --- | --- | --- | --- |
| today, margin 4 | 6.0% / 99.0% / 0.005% | 4.6% / 95.5% / 0.012% | 2.2% / 93.4% / 0.043% |
| scale 2, margin 2 | 26.0% / 99.6% / 0.002% | 24.0% / 98.5% / 0.018% | 10.8% / 96.6% / 0.056% |
| scale 2, margin 4 | 19.1% / 99.8% / 0.000% | 15.2% / 99.5% / 0.005% | 5.2% / 99.1% / 0.010% |
| scale 4, margin 0 | 25.0% / 99.5% / 0.002% | 23.2% / 98.7% / 0.021% | 10.3% / 98.1% / 0.037% |

The core read 4.9%, 5.4% and 5.1% of the slips as the intended word. Of the others, 64.7%, 68.4%
and 62.0% have the intended word among the candidates.

Against the prediction.

- `wiki-unseen`: more is fixed right than predicted, by "today" (6.0%, not 4.8% to 5.8%) and by both
  settings (26.0% and 25.0%, not 21% to 24% and 20% to 23%). Fixes right and clean words changed hit.
- `forum-unseen`: "today" hit; scale 2 with margin 2 hit on fixed right (24.0%) and fixes right
  (98.5%); scale 4 with margin 0 fixes 23.2%, a little over the predicted 23%. Clean words changed
  missed for both: 0.018% and 0.021%, not at most 0.008%.
- `social`: hit, except scale 2 with margin 2 fixed right, 10.8% and not 12% to 18%.

The pick is not confirmed. Scale 2 with margin 2 meets the bar on `wiki-unseen` and misses it on
`forum-unseen`, where it changes 12 of the words typed right (0.018%) against a bar of 0.012%, which
is what "today" changes there at margin 4 (8 words).

After the result, the words behind those shares were listed with `--changed`, added for this, on the
three frozen files and the two unseen ones (423,168 words typed right; the counts agree with the
tables). One reader sorted them, with the line in view for `forum-unseen` and from the word alone
elsewhere, counting a word as real when unsure.

| | Changed | The text had a typo, put right | A real word changed |
| --- | --- | --- | --- |
| today, margin 4 | 27 | 8 | 19 |
| scale 2, margin 2 | 24 | 10 | 14 |
| scale 2, margin 4 | 5 | 4 | 1 |

On `forum-unseen`, 8 of the 12 are typos the forum text has (`khsch`, `khhoong`, `tranhh`, `dwuaj`)
fixed to the word meant; the other 4 are `oki` once and `quad` three times. Every real word changed,
by either fix, is a foreign word or a name (`stones`, `argentine`, `olaf`, `jw`, `planets`, `voip`).

Conclusion: by the measure set before the run, margin 2 at scale 2 does not hold on unseen forum
text, so it is not the setting to ship as the default. Scale 2 with margin 4 meets the bar on all
five files, frozen and unseen: at most 0.005% of the words typed right changed, 99.5% to 99.8% of
fixes right, and 13.0% to 19.1% of the mistyped words fixed right against 4.3% to 6.0% for "today".
It was not the setting named beforehand, so this is a second pick, made on files that include the
unseen ones.

The measure itself overstates the harm on forum text: test lines carry their writers' typos, and a
fix that puts one right is counted as a clean word changed. Read by hand, the typed-keys fix at
margin 2 changes fewer real words than the fix does today at margin 4 (14 against 19 in 423,168),
all of them foreign words or names, which an input method can keep out of the fix by other means
(its own English list); that was not measured. On `social`, at the same share of words changed
(0.010%), it fixes 5.2% of the slips and "today" 1.1% (margin 6).

Limits as in the entry before: synthetic slips in assumed shares, the words before as the only
context, Telex only. The hand sorting is one reader's, after the result.

## 2026-11-27 · A search for the typed-keys fix that an input method can afford

Question: the two entries before found the candidates by typing every key string one or two slips
away through the core, too many to type when a word ends. How much of the fix is left when the
search stops at one slip, and when it also leaves out the two kinds of slip that need a key string
for every other letter?

Setup: `scripts/ngosen_near.rs` with `NGOSEN_NEAR_WAYS` and `NGOSEN_NEAR_COUNT`, on the 2,000 known
forms of the speed test (6.1 keys on average), one core:

| Search | Key strings typed per word | Time per word |
| --- | --- | --- |
| all: one slip, or two that are neither `f`, `e` nor `i` | 969 | 52.9 ms |
| `one`: one slip of any kind | 342 | 16.5 ms |
| `narrow`: one slip, neither `f` (a far key instead) nor `i` (a key left out, not of a doubled pair) | 42 | 2.2 ms |

Each string is counted once; the 3,400 of the first entry counted them as generated, repeats
included. `research.telex_typo --ways one|narrow` keeps, of the candidates the full search finds,
those such a search would find. Checked on the 2,000 forms: the driver's own narrowed search lists
the same words with the same kinds as the script's filter, 2,000 lines of 2,000, for `one` and for
`narrow`. Same table, driver, seed and files as before: the frozen `wiki`, `subs` and `forum` and
the two unseen files, marks typed, no `--rare`. The setting is scale 2 with margin 4, which met the
bar on all five; margin 2 is printed too.

Seen before this prediction: the table above; that `mguoifw` and `nguwowpif` still give `người` in
the narrow search (the extra `p` counts as `e`, 2 units, since `o` is two keys before it), that
`mguoiwff` (two slips) gives nothing in `one`, and that `zguoifw` (a far key) gives nothing in
`narrow`. No figure on the test files with `--ways`.

Prediction, before the run, scale 2, margin 4, on each of the five files. With all ways 15.8%,
13.0%, 13.6%, 19.1% and 15.2% of the mistyped words are fixed right.

- `one`: 1.0 to 1.6 points fewer fixed right: what two slips gave. Fixes right within 0.3 points
  of all ways; no more than one more clean word changed on any file.
- `narrow`: 1.8 to 3.0 points fewer than all ways. Fixes right within 0.3 points; no more than one
  more clean word changed on any file. It stays at twice what "today" fixes right on four files
  and may fall just short on `subs` (10.0% to 11.2% against 10.4%).
- At margin 2, `narrow` fixes right 2.5 to 4.5 points fewer than all ways.

The narrow search is the one to build if, at scale 2 with margin 4 on every file, it keeps at least
85% of what all ways fix right and changes at most one clean word more.

Result. `--ways all` printed the figures of the two entries before again, line for line on the
frozen files. Scale 2, margin 4 (mistyped words fixed right / fixes right / words typed right that
were changed):

| | all ways | `one` | `narrow` |
| --- | --- | --- | --- |
| `wiki` | 15.8% / 99.8% / 0.000% | 15.1% / 99.9% / 0.000% | 14.2% / 99.8% / 0.000% |
| `subs` | 13.0% / 99.7% / 0.003% | 12.8% / 99.7% / 0.003% | 12.6% / 99.5% / 0.003% |
| `forum` | 13.6% / 99.5% / 0.001% | 13.1% / 99.5% / 0.001% | 12.6% / 99.5% / 0.001% |
| `wiki-unseen` | 19.1% / 99.8% / 0.000% | 18.0% / 99.9% / 0.000% | 17.1% / 99.9% / 0.000% |
| `forum-unseen` | 15.2% / 99.5% / 0.005% | 14.8% / 99.7% / 0.006% | 14.4% / 99.7% / 0.006% |

At margin 2 the narrow search fixes right 19.8%, 21.7%, 20.0%, 22.9% and 22.0%, against 22.5%,
23.7%, 22.1%, 26.0% and 24.0% with all ways. The intended word is among the candidates of the
narrow search for 55.1%, 54.3%, 57.0%, 53.4% and 57.1% of the mistyped words, against 67.2%, 65.3%,
68.7%, 64.7% and 68.4%.

Against the prediction: the loss is smaller than predicted on four files of five.

- `one`: 0.7, 0.2, 0.5, 1.1 and 0.4 points fewer fixed right, where 1.0 to 1.6 were predicted;
  only `wiki-unseen` is in the range. Fixes right and clean words changed hit (one more word on
  `forum-unseen`).
- `narrow`: 1.6, 0.4, 1.0, 2.0 and 0.8 points fewer, where 1.8 to 3.0 were predicted; again only
  `wiki-unseen` is in the range. Fixes right within 0.2 points; one more clean word changed on
  `forum-unseen`, none elsewhere. It stays above twice "today" on every file, `subs` included
  (12.6% against 10.4%), which the prediction doubted.
- Margin 2, `narrow`: 2.7, 2.0, 2.1, 3.1 and 2.0 points fewer, where 2.5 to 4.5 were predicted.

Conclusion: the narrow search is the one to build. For 42 key strings a word in place of 969 it
keeps 89.5% to 96.9% of what all ways fix right at scale 2 with margin 4 and changes one clean word
more on one file. Two slips and the two wide kinds find the intended word for another 11 to 12
mistyped words in 100, but at 2 units or more each they seldom win by the margin. The time is the
driver's, 2.2 ms a word on one core; the input method's own search has yet to be timed. Limits as
in the two entries before.

## 2026-11-27 · The typed-keys fix in the crate

Question: does `Typing::fix_nearby` decide as `research.telex_typo` does at scale 2? Setup:
`research.telex_typo TABLE FILES --ways narrow --write-fixes OUT` on the released small table and
the five files of the entry before writes, for each distinct word shown with the words before it
that has nearby words, the fix and its margin: 36,718 decisions, 2,269 of them with no nearby word
common enough. `cargo run --release --example nearby_check TABLE OUT` pushes the words before as
typed, then the word, and asks the crate.

One thing changed in the script first, and `--ways all` printed the tables of the entry before
again with no line different: a candidate must now be a share of the table's words (1.87e-6, which
is 1,000 occurrences in this table), so the rule also means something on a small fixture table.

No prediction was written before this run; the aim of the port was the same decision on every line.
For the control the expectation was stated first: with the crate's scale set to 1, over 100
decisions on the other side of the margin and a largest difference of at least 1.0.

Result: 36,718 decisions, 36,718 the same fix, none on the other side of `FIX_MARGIN`, largest
margin difference 0; 7,910 fixes are made at the margin. The control: 36,292 the same fix, 1,762 on
the other side, largest difference 2.0. The fixture `tiny.nearby` holds eight decisions for
`cargo test`; with the scale at 1, or with two candidates of one spelling left to compete, that
test and one unit test fail and no other.

Conclusion: the crate makes the fix that was measured. What it does in an input method depends on
the nearby words that input method finds, which is not part of the crate.

## 2026-11-27 · A second decision for the typed-keys fix, once the next word is typed

Question: the typed-keys fix decides a word when it ends, with the words before it as its only
context, and at margin 4 it fixes 12.6% to 17.1% of the mistyped words. How many more does it fix
when a word that misses the margin is decided once more after the next word, with that word as
context too, and how many more of the words typed right does it change?

Setup: `research.telex_typo --then MARGIN`. A word that reaches MARGIN at its end is fixed there as
before. One that does not is rated again when the word after it ends, by every trigram that holds
it, and fixed when it then beats the runner-up and keeping by the margin of the table row; the last
word of a run gets no second decision. The word after is taken as typed right. Same table, driver,
seed and narrow search as the entry before last, scale 2, `--then 4`.

Seen before this prediction, all on the frozen `wiki`, `subs` and `forum`. A one-off script split
their 25,693 mistyped words (those the core does not read as intended): 27.5% show a word the table
has, so they are no target; 8.8% have no nearby word common enough; 8.0% have nearby words, the
intended one not among them; 55.7% have it. At the word's end the intended word is the best
candidate for 52.4%, 13.3% are fixed right at margin 4, and 38.8% have the intended word in front
but short of the margin over keeping. Of the words with the intended word nearby, 71.1% have a word
after them. Then `--then 4` on the same files (mistyped words fixed right / fixes right / words typed
right that were changed):

| | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| at the word's end, margin 4 | 14.2% / 99.8% / 0.000% | 12.6% / 99.5% / 0.003% | 12.6% / 99.5% / 0.001% |
| and again at margin 6 | 23.1% / 99.8% / 0.000% | 21.9% / 99.7% / 0.003% | 22.1% / 99.6% / 0.003% |
| and again at margin 4 | 27.3% / 99.8% / 0.001% | 27.5% / 99.7% / 0.003% | 27.0% / 99.4% / 0.005% |
| and again at margin 2 | 31.5% / 99.4% / 0.004% | 33.3% / 99.5% / 0.003% | 32.5% / 99.1% / 0.007% |

The one-off script also tried two words after: no better than one (26.2% against 27.3% over the
three files at margin 4). Nothing with `--then` was run on the unseen files.

Prediction, before the run, on the files of "The typed-keys fix on lines it was not picked on",
second decision at margin 4.

- `wiki-unseen` (17.1% / 99.9% / 0.000% at the word's end): 30.5% to 34.5% fixed right, 99.5% to
  99.9% of fixes right, at most 0.004% of the words typed right changed. At margin 2: 34.5% to 39%,
  99.0% to 99.6%, at most 0.008%.
- `forum-unseen` (14.4% / 99.7% / 0.006%): 28.5% to 32.5% fixed right, 99.0% to 99.6% of fixes
  right, 0.008% to 0.018% of the words typed right changed, most of them typos of the forum text.
  At margin 2: 33% to 38%, 98.6% to 99.3%, 0.012% to 0.025%.
- `social`, whose narrow search was not run before. At the word's end: 4.5% to 5.2% fixed right,
  98.8% to 99.4% of fixes right, 0.008% to 0.012% of the words as typed changed. With the second
  decision at margin 4: 9% to 12%, 98.0% to 99.2%, 0.02% to 0.05%.

The second decision is worth building if, at margin 4 on `wiki-unseen` and on `forum-unseen`, it
fixes right at least 1.7 times what the decision at the word's end does, at least 99% of its fixes
are right, and it changes at most 0.012% of the words typed right. The prediction for `forum-unseen`
says the last may fail by that count.

Result (mistyped words fixed right / fixes right / words typed right that were changed, of 160,078,
66,249 and 118,316; 21,112, 6,955 and 14,043 mistyped words scored). The run took 139 seconds.

| | `wiki-unseen` | `forum-unseen` | `social` |
| --- | --- | --- | --- |
| at the word's end, margin 4 | 17.1% / 99.9% / 0.000% | 14.4% / 99.7% / 0.006% | 5.0% / 99.6% / 0.006% |
| and again at margin 6 | 26.7% / 99.8% / 0.001% | 24.9% / 99.7% / 0.011% | 9.0% / 99.4% / 0.014% |
| and again at margin 4 | 30.6% / 99.8% / 0.001% | 30.1% / 99.6% / 0.017% | 12.2% / 99.1% / 0.024% |
| and again at margin 2 | 34.4% / 99.6% / 0.001% | 36.0% / 99.1% / 0.026% | 17.2% / 98.3% / 0.064% |

Against the prediction, margin 4 first.

- `wiki-unseen`: hit on all three, fixed right at the low end of the range (30.6% in 30.5% to
  34.5%). At margin 2 it fixes 34.4%, just under the predicted 34.5% to 39%.
- `forum-unseen`: hit on all three, the share of words typed right changed where predicted (0.017%
  in 0.008% to 0.018%). At margin 2 that share is 0.026%, just over the predicted 0.025%.
- `social`: at the word's end fixed right hit (5.0%), and it is safer than predicted: 99.6% of
  fixes right, not 98.8% to 99.4%, and 0.006% changed, not 0.008% to 0.012%. With the second
  decision it fixes 12.2%, just over the predicted 9% to 12%; the other two hit.

By the measure set before the run the second decision is not confirmed: it fixes right 1.8 and 2.1
times what the decision at the word's end does, with 99.8% and 99.6% of its fixes right, but on
`forum-unseen` it changes 11 of the words typed right (0.017%) against a bar of 0.012%, as the
prediction said it might.

After the result, `--changed 2 4` listed the words behind that share on the three frozen files and
the two unseen ones (423,168 words typed right), with and without `--then 4`. One reader sorted them
from the word alone, counting a word as real when unsure.

| | Changed | The text had a typo, put right | A real word changed |
| --- | --- | --- | --- |
| at the word's end, margin 4 | 6 | 3 | 3 |
| and again at margin 4 | 19 | 12 | 7 |

On `forum-unseen` 9 of the 11 are typos of the forum text fixed to the word meant (`khsch`, `khsc`,
`dwuaj`, `cihsnh`, `khhufng`, `khhoong`, `khhi`, `cuocj`, `tranhh`); the other two, `oki` and
`quant`, are changed at the word's end already. The four real words the second decision adds over
the five files are `deutscher`, `caribbe`, `empore` and `hnay` (short for `hôm nay`), next to
`stones`, `oki` and `quant`. "Today's" fix at margin 4 changes 19 real words in the same text.

Conclusion: the second decision is the largest gain measured for this fix so far. At the same margin
it about doubles the mistyped words fixed right, to 30% on unseen Wikipedia and forum text and 12% on
social-media comments, and its fixes are as often right. By the count set beforehand it fails on
unseen forum text; read by hand, what it adds there is forum typos put right, and over five files
it changes 4 more real words in 423,168, all foreign words or slang. It is built on that reading,
which was made after the result. What it costs the person typing was not measured: the word changes
after the next one is on the screen, one word behind the cursor.

Limits as before: synthetic slips in assumed shares, Telex only, and the word after is taken as
typed right. Of the mistyped words 27.5% still show a word the table has and are never looked at.

## 2026-11-27 · The second decision in the crate

Question: does a run with `Run::fixing_again` make the second decision as `research.telex_typo
--then` does? Setup: `--write-fixes OUT --then 4 --ways narrow` on the released small table and the
five files writes, for each distinct word with nearby words that has a word after it, the fix and
its margin with that word as context: 26,636 decisions. `nearby_check` pushes the words before as
typed, the word, the word after as typed, and asks `Typing::fix_nearby` about the word, which is
what the run asks when the next word ends.

Stated before the run: every decision the same, none on the other side of `FIX_MARGIN`; and for the
control, the crate's scale set to 1, over 100 decisions on the other side and a largest difference
of at least 1.0.

Result: 26,636 decisions, 26,636 the same fix, none on the other side of the margin, largest margin
difference 0; 12,943 fixes are made at the margin. The control: 26,440 the same fix, 1,404 on the
other side, largest difference 2.0. The fixture `tiny.nearby-after` holds six such decisions for
`cargo test`. In the run itself, with the second decision never made when a word is pushed, three
unit tests fail and no other; made whether or not `fixing_again` is set, one fails.

Conclusion: the crate makes the second decision that was measured. A run asks it only for the word
right before the one that just ended, once; a word taken back and typed again does not ask again.

## 2026-11-27 · Slips that land on a word the table has

Question: 27.5% of the mistyped words show a word the table has seen (`lafn` for `lafm` shows
`làn`), so the typed-keys fix never looks at them. How many does it fix when such a word is a target
too, and how many of the words typed right does it then change? Every word typed right becomes a
target, so the second number is the one that decides.

Setup: `research.telex_typo --rare N`, which makes a target of a shown word the table has seen fewer
than N times, with `--ways narrow`, scale 2 and `--then M`; the row of margin M is then the fix with
both decisions at M. Keeping the word is rated as the word itself, not as `<unk>`. N is 1,000,
100,000 and 10^12 (every word). The targets `--rare` adds are other cases than the ones without it,
whose decisions do not change, so a setting "unknown words at margin 4, known words at margin M" is
the row without `--rare` at `--then 4` plus the difference, at `--then M`, between the rows with and
without `--rare`. Same table, driver and seed as the entry before.

Prediction, before any run, on the frozen `wiki` and `forum` (27.3% / 99.8% / 0.001% and 27.0% /
99.4% / 0.005% without `--rare`: mistyped words fixed right / fixes right / words typed right that
were changed):

- Every word a target, margin 4: 33% to 40% fixed right, 95% to 98.5% of fixes right, 0.05% to 0.3%
  of the words typed right changed.
- Every word a target, the known ones at margin 8: 1 to 3 points more fixed right than without
  `--rare`, and at most 0.02% more of the words typed right changed.
- `--rare 1000`, margin 4: 1.5 to 3.5 points more fixed right, 0.005% to 0.02% of the words typed
  right changed.

Worth building if some setting, on `wiki-unseen` and on `forum-unseen`, fixes right at least 4
points more of the mistyped words than the fix does now, with at least 99% of all fixes right and
at most 0.012% of the words typed right changed. The prediction is that none does: the settings that
stay under 0.012% add 1 to 3 points.

Result on the frozen files (mistyped words fixed right / fixes right / words typed right that were
changed, of 73,104, 31,746 and 91,991; 11,026, 5,153 and 9,514 mistyped words scored). "At M" is the
setting described above: unknown words at margin 4, the known words `--rare` adds at margin M. After
the first twelve runs `--rare 10000` and `--then 10` were added, and the table of
`research.telex_typo` got its three counts: shares put together from percentages with one decimal
were up to 0.3 points off on fixes right.

| Known words that are targets | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| none, the fix as it is | 27.3% / 99.8% / 0.001% | 27.5% / 99.7% / 0.003% | 27.0% / 99.4% / 0.005% |
| every word, at 4 | 39.3% / 96.6% / 0.398% | 44.0% / 95.7% / 0.410% | 39.3% / 94.8% / 0.700% |
| every word, at 8 | 35.6% / 99.3% / 0.029% | 38.5% / 99.3% / 0.076% | 35.2% / 98.6% / 0.073% |
| seen under 100,000 times, at 8 | 34.7% / 99.4% / 0.018% | 37.6% / 99.3% / 0.050% | 34.3% / 98.7% / 0.057% |
| seen under 100,000 times, at 10 | 32.9% / 99.6% / 0.012% | 34.9% / 99.7% / 0.022% | 32.5% / 99.3% / 0.034% |
| seen under 10,000 times, at 8 | 33.1% / 99.4% / 0.005% | 36.0% / 99.5% / 0.032% | 32.9% / 98.7% / 0.029% |
| seen under 10,000 times, at 10 | 31.9% / 99.6% / 0.004% | 33.8% / 99.7% / 0.016% | 31.5% / 99.3% / 0.017% |
| seen under 1,000 times, at 4 | 33.0% / 97.9% / 0.023% | 35.2% / 97.8% / 0.016% | 32.8% / 97.8% / 0.040% |
| seen under 1,000 times, at 6 | 32.2% / 99.0% / 0.012% | 34.4% / 98.7% / 0.016% | 31.9% / 98.6% / 0.024% |
| seen under 1,000 times, at 8 | 31.4% / 99.4% / 0.003% | 33.3% / 99.5% / 0.009% | 31.0% / 99.1% / 0.016% |
| seen under 1,000 times, at 10 | 30.6% / 99.6% / 0.003% | 32.0% / 99.6% / 0.009% | 30.1% / 99.3% / 0.012% |

Against the prediction, on `wiki` and `forum`: all three missed, the same way.

- Every word a target, margin 4: fixed right hit (39.3% on both). Fixes right hit on `wiki` (96.6%)
  and fell just under on `forum` (94.8%). The words typed right changed missed: 0.398% and 0.700%,
  not 0.05% to 0.3%.
- Every word, the known ones at margin 8: 8.3 and 8.2 points more fixed right, not 1 to 3, and
  0.028% and 0.068% more of the words typed right changed, not 0.02% at most.
- `--rare 1000`, margin 4: 5.7 points more on both, not 1.5 to 3.5, and 0.023% and 0.040% of the
  words typed right changed, not 0.005% to 0.02%.

A slip onto a known word is fixed far more often than predicted, at a high margin too, and a word
typed right is changed far more often. No setting meets the bar on `forum`; "seen under 1,000 times,
at 8" and "seen under 10,000 times, at 10" meet it on `wiki` and miss on `forum` by 4 and 5 words.

After the result, `--changed 2 8 --rare 1000 --then 8` listed the 14 words typed right that the
known words at margin 8 change on the three files, and one reader sorted them with the line in view.
Eight are typos of the text put right (`hướng đẫn`, `có lé rằng`, `lịnh vực`, `xụp đổ`,
`dức hạnh`, `bõ rơi`, `đia vị`, `trằn Anh` for `Trần Anh`), one is a typo changed to another
wrong word (`dnah dự` to `đánh`), and five are real words: the brand `A'pieu` four times, changed
to `liệu`, and `empore`, which the fix as it is changes at this margin too.

Before the unseen files. The bar above cannot be met on `forum-unseen`: the fix as it is changes
0.017% of the words typed right there (11 words, 9 of them typos of the text), which was not looked
up when the bar was written. It stays as written, so by it the answer is already no. A second
reading is set here, before any run on the unseen files, of what a setting adds to the fix as it
is: at least 4 points more of the mistyped words fixed right on `wiki-unseen` and on
`forum-unseen`, at least 99% of all fixes right, and among the words typed right that it changes
and the fix as it is does not, read with the line in view and counted as real when unsure, real
words that are at most 0.006% of the words typed right (9 of 160,078 and 3 of 66,249).

The settings run are "seen under 1,000 times" and "seen under 10,000 times", each at 8 and at 10,
and "seen under 100,000 times" at 10. Prediction (30.6% / 99.8% / 0.001%, 30.1% / 99.6% / 0.017% and
12.2% / 99.1% / 0.024% as the fix is, on `wiki-unseen`, `forum-unseen` and `social`):

- Seen under 1,000 times, at 8. `wiki-unseen`: 3.5 to 5.0 points more fixed right, 99.2% to 99.7%
  of fixes right, 0.002% to 0.006% of the words typed right changed. `forum-unseen`: 3.2 to 4.8
  points more, 98.9% to 99.5%, 0.024% to 0.036%. `social`: 1.0 to 2.5 points more, 98.2% to 99.0%,
  0.030% to 0.050%.
- Seen under 10,000 times, at 10. `wiki-unseen`: 3.8 to 5.5 points more, 99.3% to 99.8%, 0.002% to
  0.008%. `forum-unseen`: 3.6 to 5.4 points more, 99.0% to 99.5%, 0.024% to 0.040%. `social`: 1.2
  to 3.0 points more, 98.2% to 99.0%, 0.030% to 0.055%.
- By the second reading "seen under 10,000 times, at 10" passes on both files, and "seen under
  1,000 times, at 8" falls short of 4 points on one of them. On `forum-unseen` 1 to 3 of the words
  either adds are real words.

Result on the unseen files (of 160,078, 66,249 and 118,316 words typed right; 21,112, 6,955 and
14,043 mistyped words scored). The row of the fix as it is repeats the entry on the second decision
to the digit. The thirteen runs, side by side, took 14 minutes.

| Known words that are targets | `wiki-unseen` | `forum-unseen` | `social` |
| --- | --- | --- | --- |
| none, the fix as it is | 30.6% / 99.8% / 0.001% | 30.1% / 99.6% / 0.017% | 12.2% / 99.1% / 0.024% |
| seen under 1,000 times, at 8 | 34.9% / 99.4% / 0.004% | 34.2% / 99.3% / 0.044% | 15.0% / 98.3% / 0.138% |
| seen under 1,000 times, at 10 | 34.1% / 99.6% / 0.001% | 33.2% / 99.4% / 0.026% | 14.1% / 98.9% / 0.086% |
| seen under 10,000 times, at 8 | 37.1% / 99.4% / 0.006% | 36.5% / 99.2% / 0.085% | 16.2% / 97.7% / 0.255% |
| seen under 10,000 times, at 10 | 35.9% / 99.6% / 0.002% | 35.0% / 99.4% / 0.038% | 14.7% / 98.8% / 0.127% |
| seen under 100,000 times, at 10 | 37.2% / 99.6% / 0.005% | 35.9% / 99.4% / 0.048% | 15.2% / 98.7% / 0.145% |

Against the prediction.

- Seen under 1,000 times, at 8. `wiki-unseen`: hit on all three (4.3 points more, 99.4%, 0.004%).
  `forum-unseen`: 4.1 points more and 99.3% hit; the words typed right changed missed, 0.044% where
  0.024% to 0.036% was predicted. `social`: 2.8 points more, just over the 1.0 to 2.5 predicted;
  98.3% hit; the words typed right changed missed by far, 0.138% where 0.030% to 0.050% was
  predicted, 163 words where the fix as it is changes 28.
- Seen under 10,000 times, at 10. `wiki-unseen` and `forum-unseen`: hit on all three (5.4 and 4.9
  points more, 99.6% and 99.4%, 0.002% and 0.038%). `social`: 2.5 points more and 98.8% hit; the
  words typed right changed missed by far, 0.127% where 0.030% to 0.055% was predicted.
- The second reading: missed for both settings, and not as predicted. Both add 4 points on both
  files with 99% of fixes right. Read with the line in view, the words typed right that only the
  setting changes are, for "seen under 1,000 times, at 8", 5 on `wiki-unseen` (1 real: the name
  `chol`) and 18 on `forum-unseen`, 4 of them real (`FDI`, `lênh đênh`, `sới bạc` and `pim`, slang
  for `phim`) against 3 allowed; the other 14 are typos of the text put right (`ban hảnh`,
  `đòng phục`, `tìm hiều`, `phầm mềm`). For "seen under 10,000 times, at 10" they are 2 on
  `wiki-unseen` (1 real: `zu`) and 14 on `forum-unseen`, at least 5 of them real (`ck`, short for
  `chồng`, three times and `nầy` twice), where 1 to 3 were predicted; for two more, `bô` and
  `gậy`, the file has a typo and a real use and the list does not say which was changed.

On `social`, which the second reading leaves out, the 20 changes made most often by "seen under
1,000 times, at 8" are 68 of its 143 at margin 8, and most are spellings the writer chose:
`ròi` (11 times), `đii`, `pà`, `nhưg`, `cviec`, `bnhieu`, `bme`, `bgio`, `khum`, `iem`, `bâyh`.
Several go to a word that was not meant: `cviec` to `việc`, `bme` to `mẹ`, `khum` to `khu`, `nhưg`
to `như`.

Conclusion: not worth building, by the bar as written and by the second reading. A slip that lands
on a rare known word can be fixed, 4 to 5 points more of the mistyped words on edited text with
99.4% of fixes right. But how often the table has seen a word does not tell a slip from a name, an
abbreviation or a chat spelling. On forum text most of what the setting changes is a typo put
right and a few real words go with them; on chat text it changes five to six times the words typed
right that the fix changes now, for 2.5 to 2.8 points more fixed. With one mistyped word in fifty,
that is one word typed right changed in about 900 against one more slip fixed in about 1,800. The
fix stays on words the table does not have.

What is left of the mistyped words, on `wiki-unseen` and `forum-unseen` with the narrow search at
margin 4: 26% and 28% show a known word (this entry); 21% and 15% have no intended word within the
narrow search (the entry on the search: all ways add 0.4 to 2.0 points at 23 times the candidates);
23% and 27% have it nearby and are not fixed, mostly short of the margin, which the strength setting
already trades against words typed right.

## 2026-11-28 · A mark key left out

Question: a Telex word with one mark key left out (`nguoif` for `nguowif`, `dduowc` for `dduowcj`)
mostly shows a word the table has seen, often a typo of its corpus (`đươc`, `ngươi`, the keys
`nguoif` themselves), so the typed-keys fix never looks at it, and the narrow search does not try a
mark key left out. How many of these does the fix put right when (a) the search tries a mark key
left out, and (b) a word the table saw rarely is a target too, but only for words that differ from
it in marks? The entry before shows that a rare known word as a target for any nearby word changes
chat spellings (`cviec` to `việc`, `khum` to `khu`); (b) cannot change letters, except where the
core shows the keys, so most of those are out of its reach. `ròi` to `rồi` is not.

Setup: `research.telex_typo` at scale 2, with `--ways marks` (the narrow search and a mark key `s f r
x j w` left out, one unit like the other near slips) and `--marks N` for (b), N 1,000, 10,000,
100,000 and 10^12. Each setting is run with `--slip mixed` (the slips of the entries before) and
`--slip mark` (each run's mistyped word has one key left out that changes only marks: a mark key
after a vowel, or the second of aa, ee, oo, dd); both have the same words typed right. As in the
entry before, "at M" means unknown words at margin 4 with the marks search, and the targets
`--marks` adds at margin M: the row of `--ways marks --then 4` plus the difference, at `--then M`,
between the rows with and without `--marks`. Same table, driver and seed as the entry before.

What this does not model: Ngó Sen marks a word typed with no mark key at all from the words around
it, so `khong` and `nguoi` are put right there before this fix; here they count as mistyped words
the fix did not fix.

Prediction, before any run, on the frozen `wiki` and `forum` (mistyped words fixed right / fixes
right / words typed right that were changed):

- `--slip mark`, the fix as it is (`--ways narrow --then 4`): 10% to 22% fixed right; a doubled
  vowel left out often shows a word the table lacks, a mark key left out rarely.
- `--slip mark`, `--ways marks`, unknown words only, at 4: 3 to 8 points more than the fix as it is.
- `--slip mark`, seen under 1,000 times, at 8: 8 to 18 points more than the fix as it is; seen
  under 10,000 times, at 10: 10 to 22 points more.
- `--slip mixed`: the marks search adds 0.3 to 1.5 points; seen under 1,000 times at 8 adds 1 to 3
  points in all, with 99% or more of fixes right.
- Words typed right changed: the marks search adds at most 0.002%. Seen under 1,000 times at 8:
  0.002% to 0.010% on `wiki`, 0.005% to 0.025% on `forum`; every word at 8: 0.02% to 0.08%.

Worth an experimental setting, off by default, if some setting, on `wiki-unseen` and on
`forum-unseen`, puts right at least 10 points more of the `--slip mark` words than the fix as it is,
keeps 99% of all fixes right with `--slip mixed`, and among the words typed right that it changes
and the fix as it is does not, read with the line in view and counted as real when unsure, has real
words at most 0.006% of the words typed right (the second reading of the entry before), with at most
0.060% of the words typed right on `social` changed in all (0.024% as the fix is; "seen under 1,000
times, at 8" of the entry before changed 0.138%).

Result on the frozen files (mistyped words fixed right / fixes right / words typed right that were
changed; the same 73,104, 31,746 and 91,991 words typed right as the entry before, and 11,026, 5,153
and 9,514 mistyped words with `--slip mixed`). The rows of the fix as it is with `--slip mixed`
repeat the entry before to the digit.

| `--slip mark` | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| the fix as it is | 3.8% / 99.5% / 0.001% | 4.2% / 99.5% / 0.003% | 3.5% / 99.7% / 0.005% |
| marks search, unknown words at 4 | 4.3% / 100.0% / 0.001% | 4.3% / 99.5% / 0.003% | 3.8% / 99.7% / 0.005% |
| seen under 1,000 times, at 8 | 9.4% / 99.9% / 0.005% | 9.0% / 99.3% / 0.016% | 8.8% / 99.5% / 0.014% |
| seen under 10,000 times, at 8 | 14.2% / 99.9% / 0.007% | 14.7% / 99.3% / 0.032% | 14.1% / 99.5% / 0.029% |
| seen under 10,000 times, at 10 | 12.1% / 99.9% / 0.004% | 12.2% / 99.5% / 0.019% | 11.6% / 99.6% / 0.017% |
| seen under 100,000 times, at 8 | 20.5% / 99.9% / 0.018% | 20.8% / 99.4% / 0.047% | 21.0% / 99.6% / 0.060% |
| seen under 100,000 times, at 10 | 16.8% / 99.9% / 0.011% | 16.3% / 99.5% / 0.028% | 16.4% / 99.7% / 0.042% |
| every word, at 8 | 45.1% / 99.9% / 0.027% | 48.3% / 99.8% / 0.072% | 45.2% / 99.7% / 0.089% |
| every word, at 10 | 34.3% / 100.0% / 0.016% | 34.8% / 99.8% / 0.038% | 32.8% / 99.8% / 0.052% |

| `--slip mixed` | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| the fix as it is | 27.3% / 99.8% / 0.001% | 27.5% / 99.7% / 0.003% | 27.0% / 99.4% / 0.005% |
| marks search, unknown words at 4 | 27.4% / 99.8% / 0.001% | 27.6% / 99.7% / 0.003% | 27.0% / 99.4% / 0.005% |
| seen under 1,000 times, at 8 | 28.7% / 99.3% / 0.005% | 29.3% / 98.8% / 0.016% | 28.7% / 98.9% / 0.014% |
| seen under 10,000 times, at 8 | 29.5% / 99.1% / 0.007% | 30.3% / 98.6% / 0.032% | 29.5% / 98.9% / 0.029% |
| seen under 10,000 times, at 10 | 29.1% / 99.5% / 0.004% | 29.7% / 99.3% / 0.019% | 29.0% / 99.2% / 0.017% |
| seen under 100,000 times, at 8 | 30.3% / 99.2% / 0.018% | 31.2% / 98.6% / 0.047% | 30.3% / 98.8% / 0.060% |
| seen under 100,000 times, at 10 | 29.7% / 99.5% / 0.011% | 30.3% / 99.3% / 0.028% | 29.6% / 99.2% / 0.042% |
| every word, at 8 | 31.3% / 99.1% / 0.027% | 32.7% / 98.5% / 0.072% | 31.3% / 98.9% / 0.089% |
| every word, at 10 | 30.4% / 99.5% / 0.016% | 31.4% / 99.3% / 0.038% | 30.3% / 99.2% / 0.052% |

Against the prediction, on `wiki` and `forum`:

- `--slip mark`, the fix as it is: missed, 3.8% and 3.5%, not 10% to 22%.
- The marks search, unknown words only: missed, 0.5 and 0.3 points, not 3 to 8.
- Seen under 1,000 times at 8: missed, 5.6 and 5.3 points, not 8 to 18. Seen under 10,000 times
  at 10: missed, 8.3 and 8.1 points, not 10 to 22.
- `--slip mixed`: the marks search adds 0.1 and 0.0 points, under 0.3 to 1.5; seen under 1,000
  times at 8 adds 1.4 and 1.7 points (hit), with 99.3% and 98.9% of fixes right, a miss on `forum`.
- Words typed right changed: the marks search adds nothing (hit); seen under 1,000 times at 8,
  0.005% and 0.014% (hit); every word at 8, 0.027% (hit) and 0.089% (missed, over 0.08%).

A mark key left out almost never shows a word the table lacks, and mostly shows a word it has seen
often: `nhưng` for `những`, `la` for `là`, `co` for `có`. Every word as a target puts right 45% of
these slips, ten times the fix as it is; the targets seen under 100,000 times, a fifth of that. So
the threshold that keeps words typed right safe also keeps most of these slips out of reach.

Before the unseen files. The bar stays as written. The settings it is read on are "seen under
10,000 times, at 8", "seen under 100,000 times, at 10" and "seen under 100,000 times, at 8"; the
others are run for the record. `--changed` lists, for each of the three, the words typed right it
changes, which are read with the line in view as in the entry before.

Prediction (30.6% / 99.8% / 0.001%, 30.1% / 99.6% / 0.017% and 12.2% / 99.1% / 0.024% with
`--slip mixed` as the fix is, on `wiki-unseen`, `forum-unseen` and `social`):

- Seen under 10,000 times, at 8: 9 to 12 points more of the `--slip mark` words put right on
  `wiki-unseen` and `forum-unseen`; with `--slip mixed` 99.0% to 99.4% of fixes right on
  `wiki-unseen` and 98.6% to 99.2% on `forum-unseen`; words typed right changed 0.004% to 0.010%,
  0.030% to 0.060% and, on `social`, 0.06% to 0.15%.
- Seen under 100,000 times, at 10: 11 to 15 points more; 99.3% to 99.6% and 99.0% to 99.4% of fixes
  right; 0.008% to 0.016%, 0.040% to 0.080% and 0.08% to 0.20%.
- Seen under 100,000 times, at 8: 15 to 19 points more; 99.0% to 99.4% and 98.6% to 99.2%; 0.015%
  to 0.025%, 0.06% to 0.10% and 0.12% to 0.30%.
- Real words among what each changes and the fix as it is does not, on `forum-unseen`: 3 to 10,
  over the 3 allowed, and `social` over 0.060% for all three. So none passes the bar.

Result on the unseen files (of 160,078, 66,249 and 118,316 words typed right; 21,112, 6,955 and
14,043 mistyped words with `--slip mixed`). The rows of the fix as it is with `--slip mixed` repeat
the entry before to the digit.

| `--slip mark` | `wiki-unseen` | `forum-unseen` | `social` |
| --- | --- | --- | --- |
| the fix as it is | 4.7% / 99.9% / 0.001% | 4.2% / 99.3% / 0.017% | 1.4% / 100.0% / 0.024% |
| marks search, unknown words at 4 | 5.3% / 99.9% / 0.001% | 4.5% / 99.7% / 0.017% | 1.6% / 100.0% / 0.024% |
| seen under 1,000 times, at 8 | 10.6% / 99.9% / 0.002% | 9.4% / 99.5% / 0.033% | 4.2% / 98.5% / 0.073% |
| seen under 10,000 times, at 8 | 16.0% / 99.9% / 0.006% | 14.8% / 99.7% / 0.059% | 6.9% / 98.5% / 0.116% |
| seen under 10,000 times, at 10 | 14.1% / 99.9% / 0.003% | 12.1% / 99.7% / 0.039% | 4.9% / 99.7% / 0.062% |
| seen under 100,000 times, at 8 | 23.3% / 99.9% / 0.016% | 21.8% / 99.8% / 0.091% | 10.2% / 98.8% / 0.151% |
| seen under 100,000 times, at 10 | 19.6% / 99.9% / 0.007% | 17.0% / 99.8% / 0.054% | 6.7% / 99.7% / 0.077% |
| every word, at 8 | 52.4% / 99.9% / 0.032% | 48.5% / 99.8% / 0.130% | 22.0% / 99.3% / 0.232% |
| every word, at 10 | 41.9% / 99.9% / 0.017% | 35.1% / 99.8% / 0.075% | 13.0% / 99.7% / 0.111% |

| `--slip mixed` | `wiki-unseen` | `forum-unseen` | `social` |
| --- | --- | --- | --- |
| the fix as it is | 30.6% / 99.8% / 0.001% | 30.1% / 99.6% / 0.017% | 12.2% / 99.1% / 0.024% |
| seen under 10,000 times, at 8 | 32.9% / 99.0% / 0.006% | 32.8% / 98.7% / 0.059% | 13.6% / 97.0% / 0.116% |
| seen under 100,000 times, at 8 | 33.7% / 99.0% / 0.016% | 33.5% / 98.7% / 0.091% | 14.0% / 96.8% / 0.151% |
| seen under 100,000 times, at 10 | 33.2% / 99.5% / 0.007% | 32.7% / 99.5% / 0.054% | 13.3% / 98.2% / 0.077% |

Against the prediction.

- Seen under 10,000 times, at 8: 11.3 and 10.6 points more (hit); 99.0% and 98.7% of fixes right
  (hit); words typed right changed 0.006% and 0.059% (hit), `social` 0.116% (hit).
- Seen under 100,000 times, at 10: 14.9 and 12.8 points more (hit); 99.5% and 99.5% of fixes
  right (hit on `wiki-unseen`; missed on `forum-unseen`, over 99.0% to 99.4%); words typed right
  changed 0.007% (missed, under 0.008%), 0.054% (hit), `social` 0.077% (missed, under 0.08%).
- Seen under 100,000 times, at 8: 18.6 and 17.6 points more (hit); 99.0% and 98.7% (hit); 0.016%
  (hit), 0.091% (hit), `social` 0.151% (hit).
- Real words among what each changes and the fix as it is does not, on `forum-unseen`, read with
  the line in view and counted as real when unsure. Seen under 10,000 times, at 8: 28 changes, 11
  real (`nầy` five times, `gậy`, `hàu`, `nhá`, `trọ`, `vùi`, `ơ`). Seen under 100,000 times, at 10:
  25 changes, 15 real (`nầy` twice, `hưu` to `hữu`, `kí` to `kĩ`, `ảo` to `áo`, `nghỉ` to `nghĩ`,
  `đam` to `đảm`, `gõ`, `gậy`, `lỗ`, `thề`, `trọ`, `xông`, `đói`, `ơ`). The other ten of these are
  typos of the text put right (`cùa`, `lơn` twice, `lằm`, `mưng`, `nết`, `rỏ`, `xuoi`, `đòng`,
  `hảnh`). Seen under 100,000 times, at 8: 49 changes, not read one by one. Over the 3 allowed for
  the two read: hit.

By the bar: no setting passes. The one closest, "seen under 100,000 times, at 10", puts right 13 to
15 points more of the words with a mark key left out, keeps 99.5% of fixes right, and on
`wiki-unseen` its real words are 6 of 160,078, under the 9 allowed; it fails on the real words of
`forum-unseen` (15 against 3) and on `social` (0.077% against 0.060%).

One flaw found in reading the lists: a candidate reached by a mark key left out is let through even
when the letters change, because `r`, `s` and `x` are letters too: `tước` to `trước` on
`wiki-unseen` (a real word, among its 6) is `r` read as the consonant of `tr`. The rule was meant
for keys the core shows as they are; it changes 1 of the 11 changes on `wiki-unseen` and none on
`forum-unseen`, so the result stands.

Conclusion: a word with a mark key left out mostly shows a real word, and a real word is often
what was typed: `nầy`, `hưu`, `kí`, `ảo`, `nghỉ` are written right far more often than they are a
slip. How rarely the table has seen a word does not tell them apart, as it did not for slips onto
other letters in the entry before. Marks-only targets do not remove the chat spellings either:
on `social` the changes made most often are `ròi` and `ồi` to `rồi`, `cọ` to `có`, `ẻm` to `em`.
What fixes these slips needs to know the word after: a later entry may try deciding the rare
known words only on the second decision, with that word as context.

## 2026-11-28 · A mark key left out, decided only once the next word ends

Question: the entry before decides a rare known word at its end, from the two words before it, and
again after the next word only when the first decision misses the margin. A guess, not checked: most
of the real words it changes (`hưu` to `hữu`, `ảo` to `áo`, `nghỉ` to `nghĩ`) are changed by that
first decision, from too little context. If a word typed with marks is decided only once the next
word ends, with that word as context too, and at a higher margin, how many of the slips are still
put right, and how many words typed right are changed?

Setup: as the entry before, with `--marks-after`, which leaves out the first decision for the
targets `--marks` adds (the words the table lacks are decided as before). `--changed` now prints the
words around each change. N is 10,000, 100,000 and 10^12, the margin 10 and 12.

How the changes are read changes too. A user of the input method, reading the lists of the entry
before, asked that the fix bring words to the standard spelling: nobody writing formally uses
`nầy` or `ròi`. So a change from a spelling no standard dictionary has (`nầy` to `này`, `ròi` and
`ồi` to `rồi`) counts as a typo put right; a real word is a standard spelling the writer meant,
read with the line in view and counted as real when unsure, as before.

Prediction, before any run, on the frozen `wiki` and `forum`, `--slip mark` (fixed right / words
typed right changed; the entry before, decided at the word's end too: 16.8% / 0.011% and 16.4% /
0.042% for "seen under 100,000 times, at 10"):

- Seen under 10,000 times, at 10: 10% to 12% and 0.002% to 0.004% on `wiki`; 9% to 11% and 0.010%
  to 0.016% on `forum`.
- Seen under 100,000 times, at 10: 13% to 16% and 0.006% to 0.009%; 12% to 15% and 0.020% to
  0.035%.
- Every word, at 12: 25% to 35% and 0.008% to 0.015%; 22% to 32% and 0.030% to 0.050%.
- With `--slip mixed`, 99.4% or more of fixes right for all six settings.

Worth an experimental setting, off by default, by the bar of the entry before (at least 10 points
more of the `--slip mark` words put right on `wiki-unseen` and `forum-unseen`, 99% of fixes right
with `--slip mixed`, real words at most 0.006% of the words typed right on both, at most 0.060% of
the words typed right on `social` changed), with real words read as above.

Result on the frozen files (`--slip mark`, then `--slip mixed`; fixed right / fixes right / words
typed right changed):

| `--slip mark` | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| the fix as it is | 3.8% / 99.5% / 0.001% | 4.2% / 99.5% / 0.003% | 3.5% / 99.7% / 0.005% |
| seen under 10,000 times, at 10 | 11.2% / 100.0% / 0.004% | 11.1% / 99.5% / 0.016% | 10.3% / 99.6% / 0.015% |
| seen under 10,000 times, at 12 | 9.2% / 100.0% / 0.004% | 9.0% / 99.6% / 0.016% | 8.4% / 99.5% / 0.011% |
| seen under 100,000 times, at 10 | 15.2% / 100.0% / 0.010% | 14.6% / 99.5% / 0.025% | 14.5% / 99.7% / 0.037% |
| seen under 100,000 times, at 12 | 12.1% / 100.0% / 0.008% | 11.3% / 99.5% / 0.022% | 11.5% / 99.6% / 0.026% |
| every word, at 10 | 30.7% / 100.0% / 0.015% | 31.1% / 99.7% / 0.032% | 29.4% / 99.8% / 0.047% |
| every word, at 12 | 22.9% / 100.0% / 0.014% | 22.1% / 99.7% / 0.028% | 21.1% / 99.8% / 0.030% |

| `--slip mixed` | `wiki` | `subs` | `forum` |
| --- | --- | --- | --- |
| the fix as it is | 27.3% / 99.8% / 0.001% | 27.5% / 99.7% / 0.003% | 27.0% / 99.4% / 0.005% |
| seen under 10,000 times, at 10 | 28.8% / 99.6% / 0.004% | 29.3% / 99.5% / 0.016% | 28.7% / 99.3% / 0.015% |
| seen under 100,000 times, at 10 | 29.3% / 99.6% / 0.010% | 29.7% / 99.5% / 0.025% | 29.3% / 99.3% / 0.037% |
| every word, at 10 | 29.9% / 99.6% / 0.015% | 30.7% / 99.4% / 0.032% | 29.9% / 99.3% / 0.047% |
| every word, at 12 | 29.4% / 99.8% / 0.014% | 29.6% / 99.7% / 0.028% | 28.9% / 99.4% / 0.030% |

Against the prediction, on `wiki` and `forum`:

- Seen under 10,000 times, at 10: hit on all four (11.2% and 0.004%, 10.3% and 0.015%).
- Seen under 100,000 times, at 10: fixed right hit (15.2%, 14.5%); words typed right changed missed,
  0.010% and 0.037%, over 0.009% and 0.035%.
- Every word, at 12: fixed right missed, 22.9% and 21.1%, under 25% and 22%; words typed right
  changed hit (0.014%, 0.030%).
- 99.4% or more of fixes right with `--slip mixed`: missed on `forum` for the three settings at 10
  (99.3%).

Waiting for the next word costs the slips little and saves the words typed right little: "seen under
100,000 times, at 10" decided at the word's end too puts right 16.8% and 16.4% and changes 0.011%
and 0.042%.

A correction to the entry before. Its real words were counted by finding the word in the file, and
where some line had it used right, the change was counted as real. With the words around each
change, which `--changed` now prints, every one of the 25 changes "seen under 100,000 times, at 10"
makes on `forum-unseen` beyond the fix as it is, and every one of its 11 on `wiki-unseen`, is a typo
of the text put right: `sở hưu chất giọng`, `khoa học kí thuật`, `anh đã nghỉ rằng`, `mặc cái ảo
ngủ`, `họ đam bảo`, `đói với`, `hoàng đế từ tước đến nay`. So that setting has no real word on
either file, not 6 and 15. On `social` its 63 changes are mostly typos put right too (`xin lõi`,
`bạn thăn`, `trang diêm`, `ròi`); about 11 are not (`mèo cọ vào chân` to `có`, `để mỡ ra` to
`mở`, `giông giống`, the name `Mỵ` to `Mỹ`, `đi quánh nhau` to `quanh`, `bả`, `bển`). This reading
was made after seeing that list, so it is no test of that setting.

Before the unseen files. The bar stays as written, and its `social` part counts every word typed
right that is changed, typos of the text put right too, which the lists show are most of them. So a
second reading, set here before these runs: as the bar, with `social` read like the other two files,
real words at most 0.010% of its words typed right (11 of 118,316). The settings read are "seen
under 100,000 times, at 10", "every word, at 10" and "every word, at 12", decided after the next word.

Prediction (as the fix is: 4.7% / 0.001%, 4.2% / 0.017% and 1.4% / 0.024% with `--slip mark` on
`wiki-unseen`, `forum-unseen` and `social`):

- Seen under 100,000 times, at 10: 11 to 14 points more on `wiki-unseen` and `forum-unseen`; words
  typed right changed 0.005% to 0.008%, 0.045% to 0.055% and 0.06% to 0.08%; real words 0 to 3, 0 to
  3 and 6 to 14.
- Every word, at 10: 22 to 30 points more on `wiki-unseen`, 20 to 28 on `forum-unseen`; 0.012% to
  0.018%, 0.06% to 0.08% and 0.09% to 0.12%; real words 1 to 6, 1 to 6 and 12 to 30.
- Every word, at 12: 15 to 22 points more on both; 0.010% to 0.016%, 0.045% to 0.065% and 0.07% to
  0.10%; real words 0 to 4, 0 to 4 and 8 to 20.
- With `--slip mixed`, 99.3% to 99.6% of fixes right on both files for all three.
- By the bar as written none passes, on `social`. By the second reading "seen under 100,000 times,
  at 10" passes and "every word, at 10" does not.

Result on the unseen files, decided after the next word:

| `--slip mark` | `wiki-unseen` | `forum-unseen` | `social` |
| --- | --- | --- | --- |
| the fix as it is | 4.7% / 99.9% / 0.001% | 4.2% / 99.3% / 0.017% | 1.4% / 100.0% / 0.024% |
| seen under 10,000 times, at 10 | 13.1% / 100.0% / 0.003% | 11.1% / 99.7% / 0.036% | 4.5% / 99.8% / 0.057% |
| seen under 10,000 times, at 12 | 11.4% / 100.0% / 0.002% | 8.9% / 99.7% / 0.024% | 3.3% / 99.8% / 0.041% |
| seen under 100,000 times, at 10 | 18.0% / 99.9% / 0.007% | 15.2% / 99.8% / 0.051% | 6.1% / 99.8% / 0.070% |
| seen under 100,000 times, at 12 | 15.1% / 100.0% / 0.005% | 11.7% / 99.7% / 0.030% | 4.2% / 99.8% / 0.048% |
| every word, at 10 | 38.0% / 99.9% / 0.016% | 31.9% / 99.9% / 0.071% | 11.8% / 99.7% / 0.098% |
| every word, at 12 | 30.0% / 99.9% / 0.008% | 22.4% / 99.8% / 0.041% | 7.0% / 99.9% / 0.061% |

| `--slip mixed` | `wiki-unseen` | `forum-unseen` | `social` |
| --- | --- | --- | --- |
| the fix as it is | 30.6% / 99.8% / 0.001% | 30.1% / 99.6% / 0.017% | 12.2% / 99.1% / 0.024% |
| seen under 100,000 times, at 10 | 32.8% / 99.7% / 0.007% | 32.4% / 99.6% / 0.051% | 13.1% / 98.6% / 0.070% |
| every word, at 10 | 33.7% / 99.6% / 0.016% | 33.0% / 99.6% / 0.071% | 13.3% / 98.6% / 0.098% |
| every word, at 12 | 32.9% / 99.8% / 0.008% | 32.1% / 99.6% / 0.041% | 12.9% / 99.0% / 0.061% |

Real words among the changes the fix as it is does not make, read with the words around each:

| Setting | `wiki-unseen` | `forum-unseen` | `social` |
| --- | --- | --- | --- |
| seen under 100,000 times, at 10 | 0 of 11 | 0 of 23 | 10 of 55 |
| every word, at 10 | 0 of 25 | 1 of 36 | 13 of 88 |
| every word, at 12 | 0 of 12 | 0 of 16 | 4 of 44 |

The real word on `forum-unseen` is `tay cụ run run`, changed to `cứ`. Those on `social`: the pun
`tư bẩn`, `cọ` twice (scrubbing, changed to `có`), the name `Mỵ` (all three settings); `bả`,
`bển`, `ẻm` (contractions of `bà ấy`, `bên ấy`, `em ấy`), `để mỡ ra` to `mở`, `đi quánh nhau` to
`quanh` and `sắp lăn rồi` (unsure) with "seen under 100,000 times"; those and `mấy ba mấy ma` to
`bà`, `e thề e` to `sẽ`, `thứ t với m` to `tư` with "every word, at 10". The rest are typos of the
text put right, or spellings no standard dictionary has: `khong` and `toi` typed without marks,
`ròi` and `ồi` to `rồi`, `nội dụng` to `nội dung`, `xây dụng`, `biểu tính`, `ghi nhân`.

Against the prediction.

- Seen under 100,000 times, at 10: 13.3 and 11.0 points more (hit); words typed right changed
  0.007%, 0.051% and 0.070% (hit); real words 0, 0 and 10 (hit); fixes right with `--slip mixed`
  99.7% on `wiki-unseen` (missed, over 99.6%) and 99.6% (hit).
- Every word, at 10: 33.3 points more on `wiki-unseen` (missed, over 22 to 30) and 27.7 on
  `forum-unseen` (hit); 0.016%, 0.071% and 0.098% (hit); real words 0 (missed, under 1 to 6), 1 and
  13 (hit); 99.6% and 99.6% (hit).
- Every word, at 12: 25.3 and 18.2 points more (missed on `wiki-unseen`, over 15 to 22; hit on
  `forum-unseen`); 0.008%, 0.041% and 0.061% (all three missed, under); real words 0, 0 (hit) and 4
  (missed, under 8 to 20); 99.8% (missed, over) and 99.6% (hit).
- By the bar as written none passes, on `social` (hit): "every word, at 12" changes 0.061% there
  against 0.060%, one word. By the second reading "seen under 100,000 times, at 10" passes and
  "every word, at 10" does not, by two real words (hit), and, not predicted, "every word, at 12"
  passes too.

Conclusion: worth an experimental setting, off by default, by the second reading. The setting is
"every word, at 12": a word typed with marks, or shown as its keys, is a target for the words that
differ from it only in marks or that a mark key left out leads to, and is decided only once the
next word ends, at margin 12. It puts right 25 and 18 points more of the words with a mark key left
out than the fix as it is (30.0% and 22.4% against 4.7% and 4.2%), keeps 99.6% or more of fixes
right on edited text, and of the 72 words typed right it changes on the three files beyond the fix
as it is, 4 are real words, all on `social`. It needs the next word, so it is for a field whose
earlier words can change, and it searches near every word typed, not only the words the table lacks.

## 2026-11-28 · A third decision for the typed-keys fix, once two words after it are typed

Question: a user typed `khaorng` for `khoảng` in a chat box, after `trong câu này chắc`, and it was
not fixed. On the released table `khoảng` is the best candidate at every stage but short of the
margin: −0.83 at the word's end, +1.81 with `ba` after it, +5.21 with `ba mươi` after it. How many
more mistyped words does the fix put right when a word that misses the margin at its end and after
the next word is decided a third time once the two words after it have ended, and how many more of
the words typed right does it change? (In that user's line the word after was `30%`; a digit ends
the run, so no later decision would have fixed it.)

Setup: `research.telex_typo --then MARGIN --then2`. A word fixed at its end or after the next word
at MARGIN is fixed as before. One that misses both is rated again with the two words after it as
context and fixed when it then beats the runner-up and keeping by the margin of the table row; a
word with fewer than two words after it in its run gets no third decision, and its second decision
must reach MARGIN. Both words after are taken as typed right. Same table, driver, seed and narrow
search as "A second decision for the typed-keys fix", scale 2; `--then 4` against `--then 4
--then2`, and `--then 2` against `--then 2 --then2`, on the three frozen files and the three unseen
ones. The one-off script of that entry rated with two words after in place of one and found it no
better (26.2% against 27.3%); a third decision only adds to the second.

Prediction, before the run, at margin 4 (fixed right / fixes right / words typed right changed; the
second decision at 4 gave 30.6% / 99.8% / 0.001%, 30.1% / 99.6% / 0.017% and 12.2% / 99.1% /
0.024%):

- `wiki-unseen`: 32% to 35% fixed right, 99.5% to 99.9% of fixes right, at most 0.004% changed.
- `forum-unseen`: 31.5% to 35%, 99.2% to 99.7%, 0.018% to 0.030%.
- `social`: 13% to 16%, 98.5% to 99.3%, 0.025% to 0.045%.
- On `wiki`, `subs` and `forum`, 1.5 to 4 points more fixed right than `--then 4` gives.

The third decision is worth building if at margin 4 it puts right at least 2 points more of the
mistyped words than the second decision does on both `wiki-unseen` and `forum-unseen`, keeps at
least 99% of fixes right on both, changes at most 0.006 points more of the words typed right on
each, and at most 0.060% of the words typed right on `social`; and if, read in context with the
rule of the entry before (a spelling no standard dictionary has counts as a typo put right), the
words it adds over the second decision on the five files hold at most 3 real words.
