"""Downloads Vietnamese Wikipedia (wikimedia/wikipedia 20231101.vi) into data/wiki.txt.gz and test/wiki.

usage: python -m research.fetch_wiki
Articles with id % 1000 == 7 are held out; up to 4,000 of their sentences (3+ words, some marks) form the test set.
"""

import gzip

import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

from . import paths
from .text import MARKED, SENTENCE_END, segments

REPO = "wikimedia/wikipedia"
FILES = [f"20231101.vi/train-0000{i}-of-00004.parquet" for i in range(4)]
TEST_SENTENCES = 4000


def usable(sentence):
    return sum(len(r) for r in segments(sentence)) >= 3 and MARKED.search(sentence.lower())


def main():
    paths.ensure()
    test = []
    with gzip.open(paths.DATA / "wiki.txt.gz", "wt", encoding="utf-8", compresslevel=3) as out:
        for name in FILES:
            local = hf_hub_download(REPO, name, repo_type="dataset", cache_dir=paths.ROOT / "hf-cache")
            t = pq.read_table(local, columns=["id", "text"])
            for aid, text in zip(t.column("id").to_pylist(), t.column("text").to_pylist()):
                if int(aid) % 1000 == 7:
                    test += [" ".join(s.split()) for s in SENTENCE_END.split(text) if usable(s)]
                else:
                    out.write(text.replace("\n", " ").strip() + "\n")
    (paths.TEST / "wiki").write_text("\n".join(test[:TEST_SENTENCES]) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
