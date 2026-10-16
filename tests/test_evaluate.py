import pytest

from research.evaluate import evaluate


def test_a_restore_that_drops_words_is_an_error(tmp_path):
    test = tmp_path / "test"
    test.write_text("tôi gõ phím\n", encoding="utf-8")
    assert evaluate(None, test, lambda run: run)["words"] == 3
    with pytest.raises(ValueError):
        evaluate(None, test, lambda run: run[:-1])
