"""Tokenizing, mark stripping and tone-placement normalization shared by every script."""

import re
import unicodedata

VI_MARKED = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
LETTERS = "a-z" + VI_MARKED
TOKEN = re.compile(f"[{LETTERS}]+|\\S")
WORD = re.compile(f"^[{LETTERS}]+$")
MARKED = re.compile(f"[{VI_MARKED}]")
# Sentence ends, as the fetch scripts split held-out text into test sentences.
SENTENCE_END = re.compile(r"[.!?\n]+")
# Old tone placement puts the mark on the first vowel of oa/oe/uy at the end of a syllable (hòa, thủy).
OLD_STYLE = re.compile("([òóỏõọ])([ae])$|([ùúủũụ])(y)$")


def normalize(text):
    return unicodedata.normalize("NFC", text).lower()


def strip_marks(word):
    decomposed = unicodedata.normalize("NFD", word.replace("đ", "d"))
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def canon(word):
    """Moves an old-style tone mark to the new position (hòa -> hoà), so both spellings count as one."""

    def move(m):
        mark, rest = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        base = strip_marks(mark)
        tone = unicodedata.normalize("NFD", mark)[1:]
        return base + unicodedata.normalize("NFC", rest + tone)

    return OLD_STYLE.sub(move, word)


def same(a, b):
    return a == b or canon(a) == canon(b)


def segments(line, tone_style=False):
    """Runs of consecutive words; punctuation, digits and symbols end a run."""
    run = []
    for tok in TOKEN.findall(normalize(line)):
        if WORD.match(tok):
            run.append(canon(tok) if tone_style else tok)
        elif run:
            yield run
            run = []
    if run:
        yield run


def marked_share(text):
    words = [w for run in segments(text) for w in run]
    if not words:
        return 0.0, 0
    return sum(bool(MARKED.search(w)) for w in words) / len(words), len(words)
