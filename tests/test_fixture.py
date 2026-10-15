from research import fixture


def test_rust_fixture_is_up_to_date(tmp_path):
    fixture.build(tmp_path)
    for name in ("tiny.timsen", "tiny.runs", "tiny.expected"):
        assert (tmp_path / name).read_bytes() == (fixture.OUT / name).read_bytes(), (
            f"{name} is stale: run python -m research.fixture"
        )
