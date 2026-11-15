# Data sources

Every corpus used to train or test a model, its licence, and whether counts derived from it may ship
in a release. "Research only" means it may be used to measure, not to build a released model, until
the licence question is answered.

| Corpus | Fetch | Licence | Ships? |
| --- | --- | --- | --- |
| Vietnamese Wikipedia, `wikimedia/wikipedia` 20231101.vi | `research.fetch_wiki` | CC BY-SA 4.0 | Yes, with attribution; the released count table is CC BY-SA 4.0 |
| OpenSubtitles 2018, monolingual vi (OPUS) | `research.fetch_subs` | No formal licence; OPUS asks for a link to opensubtitles.org and a citation (see below) | Yes, as counts only, with attribution |
| FineWeb-2 `vie_Latn` (Common Crawl, filtered by Hugging Face) | `research.fetch_fineweb` | ODC-By 1.0, plus the Common Crawl terms of use | Yes, with attribution |
| ViLexNorm social media comments (UIT), `test/social` | `research.fetch_vilexnorm` | CC BY-NC-SA 4.0, research only | Never; test only, never trained on |
| Vikey `chat_lazy` and `synthetic_lazy` (github.com/tonyminibot/Vikey), read from a local checkout, not fetched or copied here | Repository GPL-3; the files' own terms not reviewed | Never; test only, never trained on, not in this repository |
| Your own messages (`test/chat`) | `research.chat_testset` | Private | Never; test only, never committed |

## OpenSubtitles

OPUS releases the corpus without a licence. Its page asks users to link to
<http://www.opensubtitles.org/> and to cite P. Lison and J. Tiedemann, 2016, "OpenSubtitles2016:
Extracting Large Parallel Corpora from Movie and TV Subtitles", LREC 2016. It states that OPUS does
not own the text and removes material on a valid takedown request; the Hugging Face card lists the
licence as unknown.

The subtitles themselves are user translations of copyrighted films, so no clean licence exists for
the text. A release therefore ships only counts, never text: counts of syllables and of two- and
three-syllable sequences across the corpora, not sentences. `research.prune` keeps the sequences
that change restore the most until the table reaches its size. `wordfreq` ships word frequencies from the same
corpus on the same terms. Every release names OpenSubtitles with the link and the citation above. If
a takedown request reaches OPUS or us, rebuild the tables without this corpus.

## ViLexNorm

10,467 comments from Facebook, YouTube and TikTok, collected for lexical normalization by UIT
(Nguyen et al., "ViLexNorm: A Lexical Normalization Corpus for Vietnamese Social Media Text", EACL
2024; <https://github.com/ngxtnhi/ViLexNorm>). The authors release it under CC BY-NC-SA 4.0 and for
research only. NonCommercial rules out a table that may be sold under a commercial licence, and
ShareAlike would put anything trained on it under CC BY-NC-SA, which GPL does not allow; so it is a
test set and nothing else. It is also small (about 100,000 words against hundreds of millions in
the training corpora). Only the comments as typed are used; the authors' normalized versions spell
out abbreviations (`ko` → `không`), which restore deliberately keeps as typed.

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
- Technology pages (`research.fetch_fineweb tech`) are picked by host (`TECH_HOSTS`: tinhte.vn,
  voz.vn, daynhauhoc.com, viblo.asia, kipalog.com) from FineWeb-2 files 1 to 29, with a 50%
  marked-word bar, since their English terms carry no marks. The forum corpus leaves these hosts
  out, so no page is counted twice.
- Tone placement is normalized to the new style (`hoà`, `thuỷ`) before counting.
