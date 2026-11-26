from research.text import BREAK, canon, is_syllable, marked_share, same, segments, strip_marks


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


def test_segments_with_breaks_keep_runs_across_commas_and_digits():
    got = list(segments(", Gõ phím, 2 (lần) nữa. Xong!", breaks=True))
    assert got == [["gõ", "phím", BREAK, "lần", BREAK, "nữa"], ["xong"]]


def test_segments_can_normalize_tone_style():
    assert list(segments("Hòa bình", tone_style=True)) == [["hoà", "bình"]]


def test_marked_share_counts_words_with_any_mark():
    share, n = marked_share("tôi đi học ok")
    assert n == 4
    assert share == 0.75


def test_is_syllable_takes_hard_syllables_and_turns_away_typos():
    for w in ["không", "nghiêng", "khuỷu", "quyển", "giữa", "gìn", "ừ", "oẳng", "thuở", "người"]:
        assert is_syllable(w), w
    for w in ["khôgn", "đc", "sôcôla", "bcủa", "nămm", "đamg"]:
        assert not is_syllable(w), w
