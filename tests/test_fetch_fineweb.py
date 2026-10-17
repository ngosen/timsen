import pytest

pytest.importorskip("pyarrow")
pytest.importorskip("huggingface_hub")

from research.fetch_fineweb import FILE, FILES_PER_PREFIX, forum_host, tech_host  # noqa: E402


def test_a_technology_forum_page_goes_to_one_corpus_only():
    for url in ["https://voz.vn/t/ban-phim-co.123/", "https://www.tinhte.vn/thread/may-tinh.456/"]:
        assert tech_host(url)
        assert forum_host(url) is None


def test_other_forums_stay_in_the_forum_corpus():
    assert forum_host("https://www.otofun.net/threads/xe-cu.789/") == "otofun.net"
    assert tech_host("https://www.otofun.net/threads/xe-cu.789/") is None


def test_file_index_walks_every_prefix():
    names = [FILE.format(*divmod(i, FILES_PER_PREFIX)).rsplit("/", 1)[1] for i in (0, 5, 6, 29)]
    assert names == ["000_00000.parquet", "000_00005.parquet", "001_00000.parquet", "004_00005.parquet"]
