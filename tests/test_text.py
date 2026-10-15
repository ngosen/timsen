from research.text import canon, marked_share, same, segments, strip_marks


def test_strip_marks_removes_tones_hooks_and_d_bar():
    assert strip_marks("đường") == "duong"
    assert strip_marks("tiếng việt") == "tieng viet"


def test_canon_moves_old_tone_placement():
    assert canon("hòa") == "hoà"
    assert canon("thủy") == "thuỷ"
    assert canon("hoàng") == "hoàng"  # oa not at the end of the syllable stays put


def test_same_accepts_both_tone_placements_only():
    assert same("hòa", "hoà")
    assert not same("hoà", "hoá")


def test_segments_split_on_punctuation_and_digits():
    assert list(segments("Gõ phím, 2 lần nữa")) == [["gõ", "phím"], ["lần", "nữa"]]


def test_segments_can_normalize_tone_style():
    assert list(segments("Hòa bình", tone_style=True)) == [["hoà", "bình"]]


def test_marked_share_counts_words_with_any_mark():
    share, n = marked_share("tôi đi học ok")
    assert n == 4
    assert share == 0.75
