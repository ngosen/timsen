from research.repeats import measure

LINES = [
    "dạ em chào anh ạ",
    "giá bao nhiêu vậy",
    "dạ em chào chị ạ",
    "dạ em chào anh ạ",
    "giá bao nhiêu vậy",
    "dạ em gửi ạ",
]


def test_counts_repeats_and_completions_against_earlier_lines_only():
    r = measure(LINES, prefix=2, start=3)
    assert r["sents"] == 3
    # Lines 3 and 4 repeat an earlier line; line 5 does not.
    assert r["repeat"] == 2
    assert r["long"] == 3 and r["offered"] == 3
    # "dạ em" ties anh and chị once each; the latest, chị, is offered and misses line 3.
    assert r["completed"] == 1


def test_start_zero_scores_every_line():
    r = measure(LINES, prefix=2, start=0)
    assert r["sents"] == 6
    assert r["repeat"] == 2
