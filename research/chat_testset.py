"""Builds a test set from your own messages: the text the input method must get right.

usage: python -m research.chat_testset MESSAGES.txt
MESSAGES.txt is any text you wrote, one message per line. The result goes to test/chat under
DOAN_DAU_DIR (RAM by default). Never commit it or quote it: it is someone's private writing.
"""

import re
import sys

from . import paths
from .text import MARKED, segments

SPLIT = re.compile(r"[.!?\n]+")


def main():
    paths.ensure()
    sentences = []
    for message in open(sys.argv[1], encoding="utf-8"):
        for s in SPLIT.split(message):
            s = " ".join(s.split())
            if sum(len(r) for r in segments(s)) >= 3 and MARKED.search(s.lower()):
                sentences.append(s)
    (paths.TEST / "chat").write_text("\n".join(sentences) + "\n", encoding="utf-8")
    print(f"test/chat: {len(sentences)} sentences")


if __name__ == "__main__":
    main()
