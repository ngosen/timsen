"""Fixes a word whose keys slipped (mguoifw -> người), by asking which word nearby keys would have typed.

usage: python -m research.telex_typo TABLE TESTFILE... --driver NEAR DICT ENGLISH KEEP [--plain] [--rare N]
           [--changed SCALE MARGIN] [--ways all|one|narrow|marks] [--write-fixes OUT] [--then MARGIN]
           [--then2] [--marks N] [--marks-after] [--slip mixed|mark]
       python -m research.telex_typo TABLE --driver NEAR DICT ENGLISH KEEP --keys KEYS... [--after WORDS] [--rare N]

NEAR is scripts/ngosen_near.rs built against Ngó Sen's typing core; DICT, ENGLISH and KEEP are the word
lists it loads. Each word of a test file is typed as Telex keys (--plain: as its unmarked letters) and
read back through the core. A word is a fix target when the table saw what the core shows fewer than
--rare times (default: never). Its candidates are the words that keys one or two slips away would have
typed; each is scored by the trigram that ends at it, less a cost per slip, and the best one replaces
the word when it beats the next candidate and keeping the word by the margin. The word is decided when
it ends, so only the words before it are context. With --then MARGIN a word that misses that margin at
its end is decided once more when the word after it ends, with that word as context too; the margins of
the tables are then those of the second decision, and a word fixed at its end counts at every one.
--then2 decides a word that misses that margin after the next word too a third time, once the two words
after it have ended; the margins of the tables are then those of the third decision.

The clean pass counts words typed right that would be changed. The mistyped pass gives one word per
run a slip, drawn as KINDS says, and counts how often the intended word comes back; a slip the core
reads as the intended word anyway is left out. "today" is the fix the crate has now: a word shown as
unmarked letters the table lacks, one plain-letter edit away.

--keys prints, for each of the keys typed after WORDS, what the core shows and the fix with its margin
at each scale. --changed SCALE MARGIN lists, in place of the tables, each word typed right that the fix
changes at that scale and margin, with the words around it; SCALE "today" is the fix the crate has now.
--ways one keeps only the candidates one slip away, and --ways narrow leaves out of those a far key hit
instead and a key left out that is not one of a doubled pair, the two kinds that take a key string for
every other letter: what a search that types fewer key strings would find; --ways marks keeps a mark key
left out as well. --marks N makes a word the table saw fewer than N times, and at least --rare times, a
target for the words that differ from it only in marks or that a mark key left out leads to, decided
only once the next word ends with --marks-after. --slip mark gives the mistyped word of each run, in
place of a slip drawn as KINDS says, one key left out that changes only marks: a mark key after a vowel,
or the second of aa, ee, oo, dd. --write-fixes OUT writes, in place of the tables, the decision for each
word with nearby words, for the crate's nearby_check example to compare; with --then, the second
decision of each such word that has a word after it.
"""

import argparse
import os
import random
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from . import table
from .mixed_readings import telex_keys
from .model import UNK, Model
from .spellcheck import local_score
from .text import MARKED, canon, edits, normalize, same, segments, strip_marks
from .typo import known

MARGINS = [0, 2, 4, 6, 8, 10, 12]
# How much each slip costs, in units of the scale: letters as scripts/ngosen_near.rs prints them.
UNITS = {"n": 1, "s": 1, "t": 1, "r": 1, "p": 1, "m": 1, "k": 1, "e": 2, "i": 2, "f": 2.5}
SCALES = [0, 2, 4, 6]
# A candidate must itself be common, as a share of the table's words: 1,000 occurrences in the
# released small table. A table also holds the typos of its corpus.
COMMON = 1.87e-6
# The scale the crate uses (NEARBY_SCALE), for --write-fixes.
CRATE_SCALE = 2
# Each row of letter keys with how far it is shifted to the right of the top row, in key widths.
ROWS = [("qwertyuiop", 0.0), ("asdfghjkl", 0.25), ("zxcvbnm", 0.75)]
# Share of each kind of slip, assumed: a neighbouring key instead, two keys swapped, an extra key beside
# the one before or after, a key hit twice, a key left out, any other key instead, oo for ow.
KINDS = {"near": 0.35, "swap": 0.15, "beside": 0.15, "twice": 0.1, "drop": 0.15, "far": 0.05, "shape": 0.05}
# Share of mistyped words that get a second slip onto a neighbouring key.
SECOND = 0.1
LETTERS = "abcdefghijklmnopqrstuvwxyz"
# Which ways to a candidate count, each way a string with one letter per slip.
WAYS = {
    "all": lambda way: True,
    "one": lambda way: len(way) == 1,
    "narrow": lambda way: len(way) == 1 and way not in "fik",
    "marks": lambda way: len(way) == 1 and way not in "fi",
}
VOWELS = "aeiouy"


def near_keys():
    place = {c: (r, i + shift) for r, (row, shift) in enumerate(ROWS) for i, c in enumerate(row)}
    return {
        a: [b for b, (s, y) in place.items() if b != a and abs(s - r) <= 1 and abs(y - x) <= 1]
        for a, (r, x) in place.items()
    }


NEAR = near_keys()


def shape_spots(keys):
    """Places where the letter again and w each add a mark to the a or o before them."""
    return [i for i in range(1, len(keys)) if keys[i - 1] in "ao" and keys[i] in (keys[i - 1], "w")]


def slip(keys, rng, kind):
    """The keys with one slip of this kind; a kind with no place for it falls back to a neighbouring key."""
    spots = {
        "shape": shape_spots(keys),
        "swap": [i for i in range(len(keys) - 1) if keys[i] != keys[i + 1]],
    }.get(kind) or range(len(keys))
    i = rng.choice(spots)
    a, key, b = keys[:i], keys[i], keys[i + 1 :]
    if kind == "shape" and shape_spots(keys):
        return a + ("w" if key != "w" else a[-1]) + b
    if kind == "swap" and b and b[0] != key:
        return a + b[0] + key + b[1:]
    if kind == "beside":
        extra = rng.choice(NEAR[key])
        return a + rng.choice([extra + key, key + extra]) + b
    if kind == "twice":
        return a + key + key + b
    if kind == "drop" and len(keys) > 1:
        return a + b
    if kind == "far":
        return a + rng.choice([c for c in LETTERS if c != key and c not in NEAR[key]]) + b
    return a + rng.choice(NEAR[key]) + b


def mark_spots(keys):
    """Places of the keys whose loss changes only marks: a mark key after a vowel, or the second of
    aa, ee, oo, dd."""
    after_vowel = [i for i, k in enumerate(keys) if k in "sfrxjw" and any(v in keys[:i] for v in VOWELS)]
    doubled = [i for i in range(1, len(keys)) if keys[i] == keys[i - 1] and keys[i] in "aeod"]
    return sorted(after_vowel + doubled)


def mistype(keys, rng):
    """(keys with a slip, kind); one time in ten a second slip onto a neighbouring key, kind `two`."""
    kind = rng.choices(list(KINDS), weights=list(KINDS.values()))[0]
    bad = slip(keys, rng, kind)
    if rng.random() < SECOND:
        # A second slip can put the first key back.
        bad, kind = next(b for b in iter(lambda: slip(bad, rng, "near"), None) if b != keys), "two"
    return bad, kind


def through(driver, lines, known_path=None):
    """What the driver prints for each line, in order, from as many copies of it as half the cores."""
    lines = list(lines)
    cmd = list(driver) + ([known_path] if known_path else [])
    step = max(1, -(-len(lines) // max(1, (os.cpu_count() or 2) // 2)))
    chunks = [lines[k : k + step] for k in range(0, len(lines), step)]

    def run(chunk):
        out = subprocess.run(cmd, input="\n".join(chunk) + "\n", text=True, capture_output=True, check=True)
        got = out.stdout.split("\n")[: len(chunk)]
        assert len(got) == len(chunk), "the driver must print one line per word"
        return got

    with ThreadPoolExecutor(len(chunks) or 1) as pool:
        return [line for got in pool.map(run, chunks) for line in got]


def read_near(line):
    """(shown, {word: [kinds]}) from one line of the driver, the words in the table's tone placement."""
    shown, _, rest = line.partition("\t")
    words = {}
    for item in rest.split():
        word, _, kinds = item.partition("=")
        words.setdefault(canon(normalize(word)), []).extend(kinds.split(","))
    return canon(normalize(shown.strip())), words


def only(words, ways):
    """The words nearby that a way of this sort still leads to, with those ways."""
    kept = {word: [k for k in kinds if WAYS[ways](k)] for word, kinds in words.items()}
    return {word: kinds for word, kinds in kept.items() if kinds}


def units(kinds):
    """The cheapest of the ways to reach a word, each a string with one letter per slip."""
    return min(sum(UNITS[k] for k in way) for way in kinds)


def seen(m, word):
    """How often the table saw a word, or the best spelling of an unmarked form."""
    counts = [m.uni[i] for i in m.cand.get(word, [])]
    if word in m.id:
        counts.append(m.uni[m.id[word]])
    return max(counts, default=0)


def spellings(m, word):
    """The ids a candidate stands for: itself when marked, every spelling when not; None when rare."""
    if seen(m, word) < COMMON * m.total:
        return None
    if MARKED.search(word):
        return np.array([m.id[word]], dtype=np.int64)
    return m.options(word)


def rate(m, left, keep, cands, right=()):
    """(score of keeping the word, [(word, score, units)]) after the words `left` and before the words
    `right`. `cands` maps a candidate to (ids, units), and each is rated as its best spelling; `keep`
    is the id of the word."""
    seq = np.array([*left, UNK, *right], dtype=np.int64)
    rated = []
    for ids, cost in cands.values():
        s = local_score(m, seq, len(left), ids, ended=False)
        k = int(s.argmax())
        rated.append((m.words[ids[k]], s[k], cost))
    stay = local_score(m, seq, len(left), np.array([keep], dtype=np.int64), ended=False)[0]
    return stay, rated


def choose(stay, rated, scale):
    """(margin, word) of the best candidate, over the next word and over keeping; None without any."""
    best = {}
    for word, score, cost in rated:
        best[word] = max(best.get(word, -np.inf), score - scale * cost)
    if not best:
        return None
    ranked = sorted(best.items(), key=lambda x: (-x[1], x[0]))
    runner = ranked[1][1] if len(ranked) > 1 else -np.inf
    return ranked[0][1] - max(runner, stay), ranked[0][0]


def staged(rated, later, scale, then, after=False, latest=None, third=False):
    """The decision at the word's end; with a margin `then`, one that misses it is made again from
    `later`, the rating with the word after as context, and there is none without that word. With
    `after` only the decision from `later` is made. With `third`, one that misses `then` there too is
    made a third time from `latest`, the rating with the two words after, and there is none without
    them."""
    if not after:
        first = choose(*rated, scale)
        if then is None or first is None:
            return first
        if first[0] >= then:
            return np.inf, first[1]
    second = choose(*later, scale) if later else None
    if not third or second is None:
        return second
    if second[0] >= then:
        return np.inf, second[1]
    return choose(*latest, scale) if latest else None


def today(m, shown):
    """Candidates of the fix the crate has now; none when the word is not its target."""
    if not shown.isascii() or known(m, shown):
        return {}
    return {c: (m.options(c), 0) for c in edits(shown) if known(m, c)}


def nearby_words(m, shown, words, rare, marks=0):
    """Candidates among the words nearby keys would have typed; none when the word is not a target.
    A word seen at least `rare` times but fewer than `marks` is a target for the words that differ from
    it only in marks, or that a mark key left out leads to: the core shows some such slips as the keys."""
    count = seen(m, shown)
    if count >= max(rare, marks, 1):
        return {}
    if count >= max(rare, 1):
        words = {w: k for w, k in words.items() if strip_marks(w) == strip_marks(shown) or "k" in k}
    ids = {w: spellings(m, w) for w in words}
    return {w: (ids[w], units(k)) for w, k in words.items() if ids[w] is not None}


def right_ids(m, truth, i, then, words=1):
    """Ids of the `words` words after position i, for a later decision; nothing without --then or
    when fewer follow."""
    after = truth[i + 1 : i + 1 + words]
    return [] if then is None or len(after) < words else [m.id.get(w, UNK) for w in after]


def left_ids(m, truth, i, plain):
    """Ids of the words before position i: as typed with marks, or as restore guesses them."""
    if not plain:
        return [m.id.get(w, UNK) for w in truth[:i]]
    guessed = m.restore([strip_marks(w) for w in truth[:i]], ended=False) if i else []
    return [m.id.get(w, UNK) for w in guessed]


def meant(truth, plain):
    """Tells whether a word is the one meant; typed without marks, its letters are what was meant."""
    if plain:
        return lambda word: strip_marks(word) == strip_marks(truth)
    return lambda word: same(word, truth)


class Tally:
    """Per margin: decisions made, and those that gave the intended word."""

    def __init__(self):
        self.n, self.made, self.right = 0, np.zeros(len(MARGINS)), np.zeros(len(MARGINS))

    def add(self, decision, ok):
        self.n += 1
        if decision:
            hit = np.array([decision[0] >= t for t in MARGINS])
            self.made += hit
            self.right += hit & ok(decision[1])


def judge(m, cases, nearby, rare, plain, then=None, marks=0, marks_after=False, third=False):
    """Tallies of the clean and the mistyped cases for today's fix and each scale, tallies per
    (scale, kind of slip), and counts of the mistyped words: `absorbed` the core read as the intended
    word, `known` it shows as a word that is no target, `reachable` with the intended word among the
    candidates."""
    out = {name: (Tally(), Tally()) for name in ["today", *SCALES]}
    kinds, counts = {}, dict(absorbed=0, known=0, reachable=0)
    for truth, i, keys, kind in cases:
        shown, words = nearby[keys]
        ok = meant(truth[i], plain)
        if ok(shown) != (kind is None):
            counts["absorbed"] += kind is not None
            continue
        old, new = today(m, shown), nearby_words(m, shown, words, rare, marks)
        left = left_ids(m, truth, i, plain) if old or new else []
        which = 0 if kind is None else 1
        if kind:
            counts["known"] += seen(m, shown) >= max(rare, marks, 1)
            counts["reachable"] += any(ok(m.words[i]) for ids, _ in new.values() for i in ids)
        out["today"][which].add(choose(*rate(m, left, UNK, old), 0) if old else None, ok)
        keep, right = m.id.get(shown, UNK), right_ids(m, truth, i, then)
        rated = rate(m, left, keep, new) if new else None
        later = rate(m, left, keep, new, right) if new and right else None
        two = right_ids(m, truth, i, then, 2) if third else []
        latest = rate(m, left, keep, new, two) if new and two else None
        for scale in SCALES:
            after = marks_after and seen(m, shown) >= max(rare, 1)
            decision = staged(rated, later, scale, then, after, latest, third) if rated else None
            out[scale][which].add(decision, ok)
            if kind:
                kinds.setdefault((scale, kind), Tally()).add(decision, ok)
    return out, kinds, counts


def changed(m, cases, nearby, scale, margin, rare, plain, then=None, marks=0, marks_after=False, third=False):
    """(word typed right, what replaces it, by how much, the words around it) for each one the fix
    changes at this scale and margin; scale None is today's fix, which is never decided a second time."""
    for truth, i, keys, kind in cases:
        shown, words = nearby[keys]
        if kind or not meant(truth[i], plain)(shown):
            continue
        cands = today(m, shown) if scale is None else nearby_words(m, shown, words, rare, marks)
        if not cands:
            continue
        keep = UNK if scale is None else m.id.get(shown, UNK)
        left, right = left_ids(m, truth, i, plain), right_ids(m, truth, i, None if scale is None else then)
        later = rate(m, left, keep, cands, right) if right else None
        two = right_ids(m, truth, i, then, 2) if third and scale is not None else []
        latest = rate(m, left, keep, cands, two) if two else None
        after = scale is not None and marks_after and seen(m, shown) >= max(rare, 1)
        then = None if scale is None else then
        decision = staged(rate(m, left, keep, cands), later, scale or 0, then, after, latest, bool(two))
        if decision and decision[0] >= margin:
            yield truth[i], decision[1], decision[0], " ".join(truth[max(0, i - 3) : i + 4])


def write_fixes(m, cases, nearby, out, after=False):
    """One line per target that has nearby words, for the Rust check: the words before it, the word
    shown, each nearby word as WORD:UNITS, then the fix and its margin at the crate's scale, or `-`
    twice when no nearby word is common enough. With `after`, one line per target that also has a
    word after it, that word before the fix: the decision with it as context too."""
    for before, shown, words, then in cases_with_words(cases, nearby, after):
        cands = {w: (ids, units(k)) for w, k in words.items() if (ids := spellings(m, w)) is not None}
        near = " ".join(f"{w}:{units(k):g}" for w, k in sorted(words.items()))
        fix, margin = "-", "-"
        if cands:
            right = [m.id.get(w, UNK) for w in then]
            won, fix = choose(*rate(m, [m.id.get(w, UNK) for w in before], UNK, cands, right), CRATE_SCALE)
            margin = repr(float(won))
        print(" ".join(before), shown, near, *then, fix, margin, sep="\t", file=out)


def cases_with_words(cases, nearby, after=False):
    """(words before, word shown, {nearby word: [kinds]}, [word after]) of each case, once, whose
    keys have nearby words. With `after` only the cases with a word after, else that list is empty."""
    done = set()
    for truth, i, keys, _ in cases:
        shown, words = nearby[keys]
        then = truth[i + 1 : i + 2] if after else []
        key = (tuple(truth[:i]), shown, *then)
        if words and key not in done and len(then) == after:
            done.add(key)
            yield truth[:i], shown, words, then


def cases_of(path, plain, mark=False):
    """(truth, i, keys, kind) for every word typed right (kind None), then for one mistyped word per
    run that has a word of two keys or more. With `mark` the mistyped word is instead one with a key
    left out that changes only marks, in each run that has a word with such a key; the words typed
    right are the same."""
    rng, mark_rng = random.Random(11), random.Random(12)
    clean, bad = [], []
    for line in open(path, encoding="utf-8"):
        for truth in segments(line, tone_style=True):
            keys = [strip_marks(w) if plain else telex_keys(w, rng) for w in truth]
            clean += [(truth, i, k, None) for i, k in enumerate(keys)]
            spots = [i for i, k in enumerate(keys) if len(k) > 1 and k.isascii()]
            if spots:
                i = rng.choice(spots)
                slipped, kind = mistype(keys[i], rng)
                if not mark:
                    bad.append((truth, i, slipped, kind))
            marked = [i for i, k in enumerate(keys) if k.isascii() and mark_spots(k)]
            if mark and marked:
                i = mark_rng.choice(marked)
                j = mark_rng.choice(mark_spots(keys[i]))
                bad.append((truth, i, keys[i][:j] + keys[i][j + 1 :], "mark"))
    return clean + bad


def read_nearby(m, driver, cases, rare, ways="all", marks=0):
    """{keys: (shown, {word: [kinds]})}; the words nearby only for keys whose shown word is a target."""
    keys = sorted({c[2] for c in cases})
    shown = [canon(normalize(s.strip())) for s in through(driver, keys)]
    targets = [k for k, s in zip(keys, shown) if seen(m, s) < max(rare, marks, 1) and k.isascii() and k.isalpha()]
    with tempfile.NamedTemporaryFile("w", suffix=".known", encoding="utf-8") as f:
        f.write("\n".join(sorted({strip_marks(w) for w in m.id} | set(m.cand))) + "\n")
        f.flush()
        read = (read_near(line) for line in through(driver, targets, f.name))
        near = {k: (shown, only(words, ways)) for k, (shown, words) in zip(targets, read)}
    return {k: near.get(k, (s, {})) for k, s in zip(keys, shown)}


def report(name, out, kinds, counts):
    print(f"{name}: {counts['absorbed']} slips read as the intended word anyway; of the other mistyped words")
    print(f"  {counts['known']} show a word that is no target, {counts['reachable']} have the intended word nearby")
    for label, (clean, bad) in out.items():
        print(f"  {label if label == 'today' else f'scale {label}'}: {clean.n} typed right, {bad.n} mistyped")
        print("    margin  clean-changed  fixed  fixed-right  right-of-fixed  (the three counts)")
        for k, margin in enumerate(MARGINS):
            print(
                f"    {margin:6}  {clean.made[k] / max(clean.n, 1):13.3%}  {bad.made[k] / max(bad.n, 1):5.1%}  "
                f"{bad.right[k] / max(bad.n, 1):11.1%}  {bad.right[k] / max(bad.made[k], 1):14.1%}  "
                f"({clean.made[k]:g} {bad.made[k]:g} {bad.right[k]:g})",
                flush=True,
            )
    at = MARGINS.index(4)
    print("  fixed right at margin 4, by kind of slip, for each scale:")
    for kind in sorted({k for _, k in kinds}):
        row = "  ".join(f"{kinds[s, kind].right[at] / max(kinds[s, kind].n, 1):6.1%}" for s in SCALES)
        print(f"    {kind:7} {kinds[SCALES[0], kind].n:6}  {row}")


def show(m, driver, after, keys, rare, ways, marks=0):
    """Prints, for each of the keys typed after the words `after`, what is shown and the fix per scale."""
    left = [m.id.get(w, UNK) for w in after]
    nearby = read_nearby(m, driver, [(None, None, k, None) for k in keys], rare, ways, marks)
    for k in keys:
        shown, words = nearby[k]
        cands = nearby_words(m, shown, words, rare, marks)
        rated = rate(m, left, m.id.get(shown, UNK), cands)
        fixes = [choose(*rated, scale) for scale in SCALES]
        print(f"{k} -> {shown}: " + "  ".join(f"{word} {margin:+.1f}" for margin, word in filter(None, fixes)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("tests", nargs="*")
    ap.add_argument("--driver", nargs=4, required=True, metavar=("NEAR", "DICT", "ENGLISH", "KEEP"))
    ap.add_argument("--plain", action="store_true", help="type every word without marks")
    ap.add_argument("--rare", type=int, default=0, help="a word seen fewer times than this is a fix target")
    ap.add_argument("--after", default="", help="with --keys: the words typed before them")
    ap.add_argument("--keys", nargs="+", help="show the fix of each of these keys instead of scoring test files")
    ap.add_argument("--changed", nargs=2, metavar=("SCALE", "MARGIN"), help="list the clean words changed")
    ap.add_argument("--ways", choices=list(WAYS), default="all", help="which ways to a candidate count")
    ap.add_argument("--write-fixes", help="write each decision at the crate's scale to this file")
    ap.add_argument("--then", type=float, help="decide a word that misses this margin again after the next word")
    ap.add_argument("--then2", action="store_true", help="and once more after the two next words")
    ap.add_argument("--marks", type=int, default=0, help="a word seen fewer times than this is a target for marks")
    ap.add_argument("--marks-after", action="store_true", help="decide the --marks targets after the next word only")
    ap.add_argument("--slip", choices=["mixed", "mark"], default="mixed", help="the slips of the mistyped words")
    a = ap.parse_args()
    if a.marks_after and a.then is None:
        ap.error("--marks-after needs --then")
    if a.then2 and a.then is None:
        ap.error("--then2 needs --then")
    if a.then is not None and a.plain:
        ap.error("--then needs the words after as typed with marks, so it does not go with --plain")
    m = table.read(a.model) if a.model.endswith(".timsen") else Model(a.model)
    if a.keys:
        after = [canon(normalize(w)) for w in a.after.split()]
        return show(m, a.driver, after, a.keys, a.rare, a.ways, a.marks)
    for test in a.tests:
        cases = cases_of(test, a.plain, a.slip == "mark")
        nearby = read_nearby(m, a.driver, cases, a.rare, a.ways, a.marks)
        if a.write_fixes:
            with open(a.write_fixes, "a", encoding="utf-8") as out:
                write_fixes(m, cases, nearby, out, a.then is not None)
            continue
        if a.changed:
            scale = None if a.changed[0] == "today" else float(a.changed[0])
            margin = float(a.changed[1])
            args = (a.rare, a.plain, a.then, a.marks, a.marks_after, a.then2)
            for was, now, won, around in changed(m, cases, nearby, scale, margin, *args):
                print(f"{test.rsplit('/', 1)[-1]}: {was} -> {now} {won:+.1f} | {around}")
            continue
        args = (a.rare, a.plain, a.then, a.marks, a.marks_after, a.then2)
        report(test.rsplit("/", 1)[-1], *judge(m, cases, nearby, *args))


if __name__ == "__main__":
    main()
