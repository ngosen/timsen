"""Tokenizing, mark stripping and tone-placement normalization shared by every script."""

import re
import string
import unicodedata

VI_MARKED = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
LETTERS = "a-z" + VI_MARKED
TOKEN = re.compile(f"[{LETTERS}]+|\\S")
WORD = re.compile(f"^[{LETTERS}]+$")
MARKED = re.compile(f"[{VI_MARKED}]")
# Sentence ends, as the fetch scripts split held-out text into test sentences.
SENTENCE_END = re.compile(r"[.!?\n]+")
# Stands for a comma, digit or symbol inside a sentence when runs keep their context across it.
BREAK = "<p>"
VOWELS = "aăâeêioôơuưy" + "áàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
ONSETS = "ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|b|c|d|đ|g|h|k|l|m|n|p|r|s|t|v|x"
CODAS = "ch|ng|nh|c|m|n|p|t"
# The shape of one syllable, loose on purpose: it lets through some strings no dictionary has, so it
# never turns away a real syllable.
SYLLABLE = re.compile(f"^(?:{ONSETS})?[{VOWELS}]{{1,3}}(?:{CODAS})?$")
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


def segments(line, tone_style=False, breaks=False):
    """Runs of consecutive words; punctuation, digits and symbols end a run.

    With breaks, only . ! ? end a run; any other non-word tokens in a row become one BREAK inside it.
    """
    run = []
    for tok in TOKEN.findall(normalize(line)):
        if WORD.match(tok):
            run.append(canon(tok) if tone_style else tok)
        elif breaks and tok not in ".!?":
            if run and run[-1] != BREAK:
                run.append(BREAK)
        elif run:
            yield run[:-1] if run[-1] == BREAK else run
            run = []
    if run and run[-1] == BREAK:
        run.pop()
    if run:
        yield run


def marked_share(text):
    words = [w for run in segments(text) for w in run]
    if not words:
        return 0.0, 0
    return sum(bool(MARKED.search(w)) for w in words) / len(words), len(words)


def is_syllable(word):
    """Whether a lowercase word has the shape of one Vietnamese syllable (see SYLLABLE)."""
    return SYLLABLE.match(word) is not None


def edits(word):
    """Every string one edit away: replace, remove or add a letter, or swap two neighbours."""
    out = set()
    for i in range(len(word) + 1):
        a, b = word[:i], word[i:]
        if b:
            out.add(a + b[1:])
            out.update(a + c + b[1:] for c in string.ascii_lowercase)
        if len(b) > 1:
            out.add(a + b[1] + b[0] + b[2:])
        out.update(a + c + b for c in string.ascii_lowercase)
    out.discard(word)
    return out
