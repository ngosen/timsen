"""Types text through an input method's core and writes what it read, for mixed_eval to choose from.

usage: python -m research.mixed_readings TEXT DRIVER OUT [--core-fixed]
TEXT has one message per line. DRIVER is a program that reads one line of Telex keys per word on stdin
and prints what the core makes of them, one line each. OUT gets one word per line, as `truth`,
`interpreted` and `raw` between tabs, and an empty line after each run. With --core-fixed, a word the
core only lost a doubled letter of counts as read right, to show what is left once the core fixes that.
"""

import random
import subprocess
import sys
import unicodedata

from .text import canon, segments

TONE_KEYS = {"́": "s", "̀": "f", "̉": "r", "̃": "x", "̣": "j"}
SHAPE_KEYS = {"̂": None, "̆": "w", "̛": "w"}  # None: the circumflex repeats the letter
VOWELS = set("aeiouy")
# People put the tone anywhere from the vowel to the end of the word, and the raw reading depends on it.
TONE_AT_END = 0.6
TONE_AFTER_ITS_VOWEL = 0.25


def telex_keys(word, rng):
    letters, tone, tone_at = [], "", -1
    for ch in word:
        if ch == "đ":
            letters.append("dd")
            continue
        base, *marks = unicodedata.normalize("NFD", ch)
        keys = base
        for m in marks:
            if m in TONE_KEYS:
                tone, tone_at = TONE_KEYS[m], len(letters)
            else:
                keys += SHAPE_KEYS[m] or base
        letters.append(keys)
    if tone:
        r = rng.random()
        if r < TONE_AT_END:
            letters.append(tone)
        elif r < TONE_AT_END + TONE_AFTER_ITS_VOWEL:
            letters[tone_at] += tone
        else:
            last_vowel = max(i for i, k in enumerate(letters) if k[0] in VOWELS)
            letters[last_vowel] += tone
    return "".join(letters)


def lost_doubled_letter(truth, interpreted):
    """Whether the core dropped one letter of a doubled pair: `issue` read as `isue`."""
    if len(truth) != len(interpreted) + 1:
        return False
    return any(truth[i] == truth[i + 1] and truth[:i] + truth[i + 1 :] == interpreted for i in range(len(truth) - 1))


def read_through(driver, keys):
    out = subprocess.run([driver], input="\n".join(keys) + "\n", text=True, capture_output=True, check=True)
    lines = [unicodedata.normalize("NFC", line.strip().lower()) for line in out.stdout.split("\n")[: len(keys)]]
    assert len(lines) == len(keys), "the driver must print one line per word"
    return lines


def main():
    args = [a for a in sys.argv[1:] if a != "--core-fixed"]
    core_fixed = "--core-fixed" in sys.argv
    text, driver, out = args
    rng = random.Random(42)
    runs = [run for line in open(text, encoding="utf-8") for run in segments(line, tone_style=True)]
    keys = [telex_keys(w, rng) for run in runs for w in run]
    read = iter(zip(read_through(driver, keys), keys))
    with open(out, "w", encoding="utf-8") as f:
        for run in runs:
            for word in run:
                interpreted, raw = next(read)
                interpreted = canon(interpreted)
                if core_fixed and raw == word and lost_doubled_letter(word, interpreted):
                    interpreted = word
                f.write(f"{word}\t{interpreted}\t{raw}\n")
            f.write("\n")
    print(f"{len(runs):,} runs, {len(keys):,} words")


if __name__ == "__main__":
    main()
