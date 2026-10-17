"""Streams pages from FineWeb-2 vie_Latn (ODC-By) into data/<name>.txt.gz and test/<name>.

usage: python -m research.fetch_fineweb web FILE STEP MAX_WORDS   # every STEP-th row group, all pages
       python -m research.fetch_fineweb forum FILE                # whole file, discussion forums only
       python -m research.fetch_fineweb tech FILE                 # whole file, technology forums only

Pages with fewer than 60% marked words are dropped: unaccented text would teach the wrong spellings.
Technology pages mix in English words, which carry no marks, so for them the bar is 50%.
Pages with index % 1000 == 7 are held out for the test set.
"""

import gzip
import re
import sys
from collections import Counter
from urllib.parse import urlparse

import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem

from . import paths
from .text import SENTENCE_END, marked_share, segments

FILE = "datasets/HuggingFaceFW/fineweb-2/data/vie_Latn/train/{:03d}_{:05d}.parquet"
FILES_PER_PREFIX = 6  # 000_00000 to 004_00005; FILE index i is the i-th of these 30
MIN_MARKED = 0.6
MIN_MARKED_TECH = 0.5
TEST_SENTENCES = 4000
FORUM_PATH = re.compile(r"/(threads?|showthread|forums?|diendan|f\d+/|t\d+-|topic|viewtopic)", re.I)
# Classified-ad, real-estate and SEO boards repeat sales copy rather than conversation.
NOT_DISCUSSION = re.compile(
    r"raovat|rao-vat|muaban|mua-ban|\d+h?mua|mua\d|seo|ico|khachsan|giare|gia-re|"
    r"quangcao|banhang|thegioidoco|choa37|nhadat|batdongsan|bds",
    re.I,
)


# Vietnamese technology forums and developer Q&A, where English terms sit inside Vietnamese text.
TECH_HOSTS = {"tinhte.vn", "voz.vn", "daynhauhoc.com", "viblo.asia", "kipalog.com"}


def tech_host(url):
    host = urlparse(url).netloc.removeprefix("www.")
    return host if host in TECH_HOSTS else None


def forum_host(url):
    p = urlparse(url)
    host = p.netloc.removeprefix("www.")
    if NOT_DISCUSSION.search(host):
        return None
    if FORUM_PATH.search(p.path) or "forum" in host or "diendan" in host:
        return host
    return None


def run(name, file_index, groups, keep, max_words, min_marked=MIN_MARKED):
    paths.ensure()
    f = pq.ParquetFile(HfFileSystem().open(FILE.format(*divmod(file_index, FILES_PER_PREFIX)), block_size=64 << 20))
    hosts = Counter()
    n = words = 0
    test = []
    suffix = f"-{file_index}" if name in ("forum", "tech") else ""
    with gzip.open(paths.DATA / f"{name}{suffix}.txt.gz", "wt", encoding="utf-8", compresslevel=3) as out:
        for g in groups(f.num_row_groups):
            t = f.read_row_group(g, columns=["text", "url"])
            for text, url in zip(t.column("text").to_pylist(), t.column("url").to_pylist()):
                n += 1
                host = keep(url)
                if not host:
                    continue
                share, count = marked_share(text)
                if share < min_marked:
                    continue
                if n % 1000 == 7:
                    test += [
                        " ".join(s.split()) for s in SENTENCE_END.split(text) if sum(len(r) for r in segments(s)) >= 3
                    ]
                    continue
                words += count
                hosts[host] += 1
                out.write(text.replace("\n", " ").strip() + "\n")
            if max_words and words >= max_words:
                break
    (paths.TEST / f"{name}{suffix}").write_text("\n".join(test[:TEST_SENTENCES]) + "\n", encoding="utf-8")
    kept = min(len(test), TEST_SENTENCES)
    print(f"{name}{suffix}: pages {sum(hosts.values()):,} words {words:,} test sentences {kept}")
    print("top hosts:", ", ".join(f"{h} {c}" for h, c in hosts.most_common(25)))


def main():
    kind, file_index = sys.argv[1], int(sys.argv[2])
    if kind == "web":
        step, max_words = int(sys.argv[3]), int(sys.argv[4])
        run(
            "web",
            file_index,
            lambda total: range(0, total, step),
            lambda url: urlparse(url).netloc.removeprefix("www."),
            max_words,
        )
    elif kind == "forum":
        run("forum", file_index, range, forum_host, 0)
    elif kind == "tech":
        run("tech", file_index, range, tech_host, 0, MIN_MARKED_TECH)
    else:
        sys.exit("kind must be web, forum or tech")


if __name__ == "__main__":
    main()
