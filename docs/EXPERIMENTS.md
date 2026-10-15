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
