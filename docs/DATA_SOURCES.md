# Data sources

Every corpus used to train or test a model, its licence, and whether counts derived from it may ship
in a release. "Research only" means it may be used to measure, not to build a released model, until
the licence question is answered.

| Corpus | Fetch | Licence | Ships? |
| --- | --- | --- | --- |
| Vietnamese Wikipedia, `wikimedia/wikipedia` 20231101.vi | `research.fetch_wiki` | CC BY-SA 4.0 | Yes, with attribution; the released count table is CC BY-SA 4.0 |
| OpenSubtitles 2018, monolingual vi (OPUS) | `research.fetch_subs` | Subtitles are user translations from opensubtitles.org; redistribution terms unclear | Research only |
| FineWeb-2 `vie_Latn` (Common Crawl, filtered by Hugging Face) | `research.fetch_fineweb` | ODC-By 1.0, plus the Common Crawl terms of use | Yes, with attribution |
| Your own messages (`test/chat`) | `research.chat_testset` | Private | Never; test only, never committed |

## Considered and not used

- **UIT-ViHSD** (social media comments, UIT): the authors limit it to research, access is gated, and
  it is small (33,400 comments).
- **CulturaX** (mC4 + OSCAR): gated behind accepting terms; FineWeb-2 covers the same Common Crawl text
  without a gate.
- **Scraping forums or Facebook directly**: against the sites' terms, and the posts belong to their
  authors. Forum text is taken from FineWeb-2 instead, which follows `robots.txt`.

## Filtering

- Pages with fewer than 60% words carrying a mark are dropped (`MIN_MARKED`): unaccented text would
  teach the wrong spellings.
- Forum pages are picked by URL (`/threads/`, `/showthread`, `forum` in the host, …); classified-ad,
  real-estate and SEO hosts are dropped (`NOT_DISCUSSION` in `research/fetch_fineweb.py`).
- Tone placement is normalized to the new style (`hoà`, `thuỷ`) before counting.
