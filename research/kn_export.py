"""Writes corpora as one run of syllables per line for KenLM, plus a capped vocabulary.

usage: python -m research.kn_export OUT_DIR CORPUS...
Writes OUT_DIR/corpus.txt and OUT_DIR/vocab.txt (the most frequent words, at most VOCAB_CAP, so word
ids fit in 16 bits and four of them pack into one 64-bit key). Pass vocab.txt to lmplz with
--limit_vocab_file; rarer words become <unk>.
"""

import sys
from collections import Counter
from pathlib import Path

from .text import segments
from .train import chunks

VOCAB_CAP = 65_000


def main():
    out, names = Path(sys.argv[1]), sys.argv[2:]
    out.mkdir(parents=True, exist_ok=True)
    words = Counter()
    with open(out / "corpus.txt", "w", encoding="utf-8") as f:
        for lines in chunks(names):
            for text in lines:
                for run in segments(text, tone_style=True):
                    words.update(run)
                    f.write(" ".join(run) + "\n")
    kept = [w for w, _ in words.most_common(VOCAB_CAP)]
    (out / "vocab.txt").write_text(" ".join(kept) + "\n", encoding="utf-8")
    covered = sum(words[w] for w in kept) / sum(words.values())
    print(f"tokens {sum(words.values()):,} distinct {len(words):,} kept {len(kept):,} covering {covered:.4%}")


if __name__ == "__main__":
    main()
