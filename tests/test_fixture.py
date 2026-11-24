import numpy as np

from research import fixture, table
from research.model import SHIFT


def test_rust_fixture_is_up_to_date(tmp_path):
    fixture.build(tmp_path)
    names = ("tiny.timsen", "tiny.runs", "tiny.expected", "tiny.learned", "tiny.personal.expected")
    for name in (*names, "long.timsen", "long.runs", "long.expected"):
        assert (tmp_path / name).read_bytes() == (fixture.OUT / name).read_bytes(), (
            f"{name} is stale: run python -m research.fixture"
        )


def test_the_long_table_has_a_long_trigram_group_that_decides_a_restoration():
    buf = (fixture.OUT / "long.timsen").read_bytes()
    assert table.HEADER.unpack_from(buf)[2] >= 1
    t = table.read(fixture.OUT / "long.timsen")
    lengths = np.diff(np.flatnonzero(np.diff(t.tk >> SHIFT, prepend=-1, append=-1)))
    assert lengths.max() >= table.LONG
    assert t.restore(["ta", "co", "ba"]) == ["ta", "có", "bá"]
    assert t.restore(["anh", "thay", "ba"]) == ["anh", "thấy", "bà"]
