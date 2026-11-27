"""Builds the small table the Rust tests compare against, from a few made-up sentences.

usage: python -m research.fixture [OUT_DIR]   (default: crates/timsen/tests/fixtures)
Writes tiny.timsen, tiny.runs and tiny.expected, for the personal dictionary tiny.learned and
tiny.personal.expected, for fixing unknown syllables tiny.fixes, and for fixing them to words near
their keys tiny.nearby, and decided once more with the word after tiny.nearby-after. long.timsen, long.runs and
long.expected are a second table where one pair of words has hundreds of continuations. Rerun after
changing the table format or the model.
"""

import gzip
import sys
import tempfile
from pathlib import Path
from unittest import mock

from . import crosscheck, paths, table, telex_typo, train, typo
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
# (words before, word shown, {nearby word: [kinds of slip]}): a slip in context, the same word reached
# with and without marks, two words that compete, one too costly, words the table lacks, a marked
# syllable nothing knows, a capital, and a word at the start of a run.
NEARBY = [
    ("tôi gõ", "phsifm", {"phím": ["n"], "nhanh": ["f"]}),
    ("tôi gõ", "phsim", {"phim": ["n"], "phím": ["nn", "t"]}),
    ("nhà ta có", "gox", {"gỗ": ["s"], "gõ": ["s"]}),
    ("bàn", "phmi", {"phím": ["e"], "này": ["f"]}),
    ("tôi gõ", "xyzzy", {"zzz": ["n"], "phmí": ["n"]}),
    ("chúc anh", "khoẻj", {"khoẻ": ["p"], "mạnh": ["f"]}),
    ("tôi gõ", "Phsifm", {"phím": ["n"]}),
    ("", "ngwoif", {"người": ["m"], "tôi": ["nn"]}),
]
# (words before, word shown, nearby words, word after): the word after settles a tie, lifts a fix that
# was short of the margin, picks the other of two words, and is itself a word the table lacks.
NEARBY_AFTER = [
    ("", "ngwoif", {"người": ["m"], "tôi": ["nn"]}, "ta"),
    ("nhà ta có", "gox", {"gỗ": ["s"], "gõ": ["s"]}, "quý"),
    ("người ta có", "gox", {"gỗ": ["s"], "gõ": ["s"]}, "cửa"),
    ("bàn", "phmi", {"phím": ["e"], "này": ["f"]}, "này"),
    ("tôi gõ", "xyzzy", {"zzz": ["n"], "phmí": ["n"]}, "rất"),
    ("tôi gõ", "Phsifm", {"phím": ["n"]}, "xyzzy"),
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


def write_nearby(m, path):
    """The decisions of research.telex_typo for NEARBY, as its --write-fixes writes them."""
    cases = [(before.split() + [shown], len(before.split()), shown, None) for before, shown, _ in NEARBY]
    nearby = {shown: (shown, words) for _, shown, words in NEARBY}
    with open(path, "w", encoding="utf-8") as f:
        telex_typo.write_fixes(m, cases, nearby, f)
    cases = [
        (before.split() + [shown, after], len(before.split()), shown, None) for before, shown, _, after in NEARBY_AFTER
    ]
    with open(path.with_name(path.name + "-after"), "w", encoding="utf-8") as f:
        telex_typo.write_fixes(m, cases, {shown: (shown, words) for _, shown, words, _ in NEARBY_AFTER}, f, True)


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
        write_nearby(table.read(out / "tiny.timsen"), out / "tiny.nearby")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
