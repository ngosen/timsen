"""Downloads OpenSubtitles 2018 monolingual Vietnamese (OPUS) into data/subs.txt.gz and test/subs.

usage: python -m research.fetch_subs
Line n with n % 1000 == 7 is held out. Research use only until the licence for redistributing counts
derived from it is clear (docs/DATA_SOURCES.md).
"""

import gzip
import urllib.request

from . import paths
from .text import MARKED, segments

URL = "https://object.pouta.csc.fi/OPUS-OpenSubtitles/v2018/mono/vi.txt.gz"
TEST_SENTENCES = 4000


def usable(sentence):
    return sum(len(r) for r in segments(sentence)) >= 3 and MARKED.search(sentence.lower())


def main():
    paths.ensure()
    raw = paths.ROOT / "subs-raw.txt.gz"
    if not raw.exists():
        urllib.request.urlretrieve(URL, raw)
    test = []
    with (
        gzip.open(raw, "rt", encoding="utf-8", errors="ignore") as f,
        gzip.open(paths.DATA / "subs.txt.gz", "wt", encoding="utf-8", compresslevel=3) as out,
    ):
        for n, line in enumerate(f):
            if n % 1000 != 7:
                out.write(line)
            elif len(test) < TEST_SENTENCES and usable(line):
                test.append(" ".join(line.split()))
    (paths.TEST / "subs").write_text("\n".join(test) + "\n", encoding="utf-8")
    raw.unlink()


if __name__ == "__main__":
    main()
