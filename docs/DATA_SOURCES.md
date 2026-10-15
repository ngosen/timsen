# Data sources

Every corpus used to train or test a model, its licence, and whether counts derived from it may ship
in a release. "Research only" means it may be used to measure, not to build a released model, until
the licence question is answered.

| Corpus | Fetch | Licence | Ships? |
| --- | --- | --- | --- |
| Vietnamese Wikipedia, `wikimedia/wikipedia` 20231101.vi | `research.fetch_wiki` | CC BY-SA 4.0 | Yes, with attribution; the released count table is CC BY-SA 4.0 |
| OpenSubtitles 2018, monolingual vi (OPUS) | `research.fetch_subs` | No formal licence; OPUS asks for a link to opensubtitles.org and a citation (see below) | Yes, as counts only, with attribution |
| FineWeb-2 `vie_Latn` (Common Crawl, filtered by Hugging Face) | `research.fetch_fineweb` | ODC-By 1.0, plus the Common Crawl terms of use | Yes, with attribution |
| Your own messages (`test/chat`) | `research.chat_testset` | Private | Never; test only, never committed |

## OpenSubtitles

OPUS releases the corpus without a licence. Its page asks users to link to
<http://www.opensubtitles.org/> and to cite P. Lison and J. Tiedemann, 2016, "OpenSubtitles2016:
Extracting Large Parallel Corpora from Movie and TV Subtitles", LREC 2016. It states that OPUS does
not own the text and removes material on a valid takedown request; the Hugging Face card lists the
licence as unknown.

The subtitles themselves are user translations of copyrighted films, so no clean licence exists for
the text. A release therefore ships only counts, never text: three-syllable sequences seen at least
50 times (small table) or 5 times (large table) across the corpora, not sentences. `wordfreq` ships word frequencies from the same
corpus on the same terms. Every release names OpenSubtitles with the link and the citation above. If
a takedown request reaches OPUS or us, rebuild the tables without this corpus.

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
