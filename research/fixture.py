"""Builds the small table the Rust tests compare against, from a few made-up sentences.

usage: python -m research.fixture [OUT_DIR]   (default: crates/timsen/tests/fixtures)
Writes tiny.timsen, tiny.runs and tiny.expected, for the personal dictionary tiny.learned and
tiny.personal.expected, and for fixing unknown syllables tiny.fixes. long.timsen, long.runs and
long.expected are a second table where one pair of words has hundreds of continuations. Rerun after
changing the table format or the model.
"""

import gzip
import sys
import tempfile
from pathlib import Path
from unittest import mock

from . import crosscheck, paths, table, train, typo
from .model import Model

OUT = Path(__file__).resolve().parent.parent / "crates" / "timsen" / "tests" / "fixtures"
# Made up for the fixture; covers context choices, new tone placement (hoà, thuỷ, khoẻ), qu/gi
# clusters, unmarked and unknown words.
CORPUS = [
    "tôi gõ phím rất nhanh",
    "bàn phím này gõ rất êm",
    "cái bàn bằng gỗ lim",
    "nhà ta có gỗ quý",
    "người ta có gõ cửa",
    "hoà bình và thuỷ lợi",
    "chúc anh khoẻ mạnh",
    "quý khách vui lòng chờ",
    "gia đình tôi ở hà nội",
    "mở file code ra xem",
    # gõ is likelier after "bạn thích", but only gỗ ends a run: an open run and an ended one differ.
    "bạn thích gỗ",
    "bạn thích gõ phím",
    "bạn thích gõ phím",
] * 6
TEST = [
    "Tôi gõ phím rất nhanh, bàn phím này gõ rất êm.",
    "Nhà ta có gỗ quý; người ta có gõ cửa.",
    "Hoà bình và thuỷ lợi. Chúc anh khoẻ mạnh!",
    "Quý khách vui lòng chờ, gia đình tôi ở Hà Nội.",
    "Mở file code ra xem commit mới.",
    "gõ",
    "Bạn thích gỗ.",
]
# The user's own text: it turns gỗ quý into gõ quý and makes gõ end a run. The last line has a word
# the table lacks, so crosscheck leaves it out.
PERSONAL = ["nhà ta có gõ quý", "bạn thích gõ", "tôi thích ngó sen"]
# Unmarked runs with typos the table does not know (phmi, rta, quyy), a known word one edit from
# another, words with nothing known one edit away (commit, xyzzy) and one typed with capitals.
FIX_RUNS = [
    "toi go phmi rat nhanh",
    "ban phmi nay go rta em",
    "nha ta co go quyy",
    "chuc anh khoe mnah",
    "mo fiel code ra xem commit",
    "Tooi go Phmi",
    "xyzzy",
    "gia dinh toi o ha noii",
]
# Syllables that follow "ta có" with a rising tone and "anh thấy" with a falling one, which is the
# commoner of the two: only the trigram after "ta có" restores the rising one.
LONG_SYLLABLES = [
    o + r for o in "bcdghklmnprstvx" for r in "a e i o u an en in on un am em im om um ang ong ung anh inh ay".split()
]
RISING, FALLING = str.maketrans("aeiou", "áéíóú"), str.maketrans("aeiou", "àèìòù")
LONG_OTHERS = ["ta về nhà rồi", "ta ăn cơm rồi", "ta đi chợ rồi", "ta xem phim rồi"]


def marked(syllable, tones):
    """The syllable with a tone on its last vowel."""
    at = max(i for i, c in enumerate(syllable) if c in "aeiou")
    return syllable[:at] + syllable[at].translate(tones) + syllable[at + 1 :]


def long_corpus():
    lines = [f"ta có {marked(s, RISING)}" for s in LONG_SYLLABLES] * 5
    lines += [f"anh thấy {marked(s, FALLING)}" for s in LONG_SYLLABLES] * 7
    return lines + LONG_OTHERS * 5


def long_test():
    picked = LONG_SYLLABLES[::7]
    lines = [f"ta có {marked(s, RISING)}, anh thấy {marked(s, FALLING)}." for s in picked]
    return lines + [f"{marked(s, FALLING)} {marked(s, RISING)}" for s in picked[:5]] + LONG_OTHERS


def build_table(tmp, out, name, corpus, test):
    """Trains on the corpus, writes NAME.timsen and how it restores the runs of the test lines."""
    with gzip.open(tmp / f"{name}.txt.gz", "wt", encoding="utf-8") as f:
        f.write("\n".join(corpus) + "\n")
    argv = ["train", str(tmp / f"{name}.npz"), name]
    with mock.patch.object(paths, "DATA", tmp), mock.patch.object(sys, "argv", argv):
        with mock.patch.object(train, "WORKERS", 1):
            train.main()
    table.write(Model(tmp / f"{name}.npz"), out / f"{name}.timsen")
    (tmp / "test").write_text("\n".join(test) + "\n", encoding="utf-8")
    crosscheck.write(out / f"{name}.timsen", tmp / "test", out / f"{name}.runs", out / f"{name}.expected")


def build(out):
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        build_table(tmp, out, "long", long_corpus(), long_test())
        build_table(tmp, out, "tiny", CORPUS, TEST)
        (tmp / "personal").write_text("\n".join(PERSONAL) + "\n", encoding="utf-8")
        learned, expected = out / "tiny.learned", out / "tiny.personal.expected"
        crosscheck.write_personal(out / "tiny.timsen", tmp / "personal", out / "tiny.runs", learned, expected)
        with open(out / "tiny.fixes", "w", encoding="utf-8") as f:
            typo.write_fixes(table.read(out / "tiny.timsen"), [r.split(" ") for r in FIX_RUNS], f)


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
