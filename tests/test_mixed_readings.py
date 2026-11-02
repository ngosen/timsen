import random
import sys

from research import mixed_readings as mr


def test_telex_keys_give_the_word_back_as_keys():
    rng = random.Random(1)
    assert mr.telex_keys("test", rng) == "test"
    assert mr.telex_keys("đi", rng) == "ddi"
    assert sorted(mr.telex_keys("tiếng", random.Random(s)) for s in range(50))[0] in ("tieengs", "tieesng")
    assert all(sorted(mr.telex_keys("có", random.Random(s))) == sorted("cos") for s in range(20))


def test_a_lost_doubled_letter_is_told_from_other_changes():
    assert mr.lost_doubled_letter("issue", "isue")
    assert mr.lost_doubled_letter("coffee", "cofee")
    assert not mr.lost_doubled_letter("test", "tét")
    assert not mr.lost_doubled_letter("toast", "tost")


def test_writes_truth_interpreted_and_raw_per_run(tmp_path, monkeypatch):
    # A stand-in core that drops one `s`, marks `test` and spells `tieengs` as it should.
    driver = tmp_path / "driver"
    driver.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        "for line in sys.stdin:\n"
        "    w = line.strip()\n"
        "    print({'issue': 'isue', 'test': 'tét'}.get(w, 'tiếng' if w.startswith('tie') else w))\n"
    )
    driver.chmod(0o755)
    text = tmp_path / "text"
    text.write_text("issue test, tiếng\n", encoding="utf-8")

    def rows(*flags):
        out = tmp_path / "out"
        monkeypatch.setattr(sys, "argv", ["mixed_readings", str(text), str(driver), str(out), *flags])
        mr.main()
        return out.read_text(encoding="utf-8").split("\n")

    plain = rows()
    assert plain[0] == "issue\tisue\tissue"
    assert plain[1] == "test\ttét\ttest"
    assert plain[2] == ""
    assert plain[3].startswith("tiếng\ttiếng\ttie")
    assert rows("--core-fixed")[:2] == ["issue\tissue\tissue", "test\ttét\ttest"]
