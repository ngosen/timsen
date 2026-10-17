"""Downloads the ViLexNorm social media comments into test/social. Test only: never written to data/.

usage: python -m research.fetch_vilexnorm
The comments are kept as typed (the `original` column), with their abbreviations, since restore keeps
those as typed too. A comment is used when it has at least three words and at least half of them
carry a mark; comments typed without marks cannot score restore. CC BY-NC-SA 4.0, research only
(docs/DATA_SOURCES.md).
"""

import csv
import io
import urllib.request

from . import paths
from .text import marked_share

# Fixed so the test set cannot change under a series of runs.
REVISION = "1070c6b9b008"
URL = "https://raw.githubusercontent.com/ngxtnhi/ViLexNorm/{}/data/{}.csv"
MIN_MARKED = 0.5


def comments():
    for split in ("train", "dev", "test"):
        with urllib.request.urlopen(URL.format(REVISION, split)) as r:
            yield from (row["original"] for row in csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def main():
    paths.ensure()
    test = []
    for text in comments():
        text = " ".join(text.split())
        share, words = marked_share(text)
        if words >= 3 and share >= MIN_MARKED:
            test.append(text)
    (paths.TEST / "social").write_text("\n".join(test) + "\n", encoding="utf-8")
    print(f"test/social: {len(test)} comments")


if __name__ == "__main__":
    main()
