"""Writes the held-out Wikipedia sentences that test/wiki does not use, as a second test file.

usage: python -m research.wiki_rest OUT
test/wiki is the first 4,000 usable sentences of the articles with id % 1000 == 7. The later ones
are in neither the test set nor the training text, so a setting picked on test/wiki can be checked
on them.
"""

import sys
from pathlib import Path

import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

from . import paths
from .fetch_wiki import FILES, REPO, TEST_SENTENCES, usable
from .text import SENTENCE_END


def held_out(articles):
    """The usable sentences of the held-out (id, text) articles, in order."""
    return [
        " ".join(s.split())
        for aid, text in articles
        if int(aid) % 1000 == 7
        for s in SENTENCE_END.split(text)
        if usable(s)
    ]


def articles():
    for name in FILES:
        local = hf_hub_download(REPO, name, repo_type="dataset", cache_dir=paths.ROOT / "hf-cache")
        t = pq.read_table(local, columns=["id", "text"])
        yield from zip(t.column("id").to_pylist(), t.column("text").to_pylist())


def main():
    paths.ensure()
    sentences = held_out(articles())
    known = (paths.TEST / "wiki").read_text(encoding="utf-8").splitlines()
    if sentences[:TEST_SENTENCES] != known:
        sys.exit("the first held-out sentences are not test/wiki: another dump?")
    Path(sys.argv[1]).write_text("\n".join(sentences[TEST_SENTENCES:]) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
