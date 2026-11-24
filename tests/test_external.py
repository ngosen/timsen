import pytest

from research import external
from research.evaluate import evaluate

SENTENCES = "Tôi gõ phím, rồi nghỉ 5 phút.\nHoà bình!\n"


@pytest.fixture
def test_file(tmp_path):
    path = tmp_path / "test"
    path.write_text(SENTENCES, encoding="utf-8")
    return path


def restored(tmp_path, text):
    path = tmp_path / "restored"
    path.write_text(text, encoding="utf-8")
    return path


def test_strip_keeps_punctuation_and_removes_marks(test_file, capsys):
    external.strip(test_file, runs=False)
    assert capsys.readouterr().out == "toi go phim, roi nghi 5 phut.\nhoa binh!\n"
    external.strip(test_file, runs=True)
    assert capsys.readouterr().out == "toi go phim\nroi nghi\nphut\nhoa binh\n"


def test_both_scores_count_the_words_evaluate_counts(test_file, tmp_path):
    words = evaluate(None, test_file, lambda run: run)["words"]
    whole = external.score_sentences(test_file, restored(tmp_path, SENTENCES.lower()))
    assert (whole["words"], whole["word"], whole["sent"]) == (words, 1.0, 1.0)
    by_run = external.score_runs(test_file, restored(tmp_path, "tôi gõ phím\nrồi nghỉ\nphút\nhoà bình\n"))
    assert (by_run["words"], by_run["word"]) == (words, 1.0)


def test_unrestored_and_old_tone_placement(test_file, tmp_path):
    # Only "5" needs no mark, and it is not a word; hòa and hoà are one spelling.
    plain = external.score_sentences(test_file, restored(tmp_path, "toi go phim, roi nghi 5 phut.\nhòa binh!\n"))
    assert (plain["words"], plain["word"], plain["sent"]) == (8, 1 / 8, 0.0)


def test_shifted_output_is_an_error(test_file, tmp_path):
    with pytest.raises(ValueError):
        external.score_sentences(test_file, restored(tmp_path, "tôi gõ, rồi nghỉ 5 phút.\nhoà bình!\n"))
    with pytest.raises(ValueError):
        external.score_sentences(test_file, restored(tmp_path, "tôi gõ phím, rồi nghỉ 5 phút.\n"))
    with pytest.raises(ValueError):
        external.score_runs(test_file, restored(tmp_path, "tôi gõ phím\nrồi nghỉ\nphút\nhoà bình\nthừa\n"))


def test_a_stray_combining_mark_does_not_join_the_word_before_it(tmp_path, capsys):
    path = tmp_path / "test"
    path.write_text("mẹ về\u0300 rồi\n", encoding="utf-8")
    external.strip(path, runs=False)
    plain = capsys.readouterr().out
    assert plain == "me ve  roi\n"
    assert external.score_sentences(path, restored(tmp_path, plain))["words"] == 3
