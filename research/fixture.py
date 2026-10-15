"""Builds the small table the Rust tests compare against, from a few made-up sentences.

usage: python -m research.fixture [OUT_DIR]   (default: crates/timsen/tests/fixtures)
Writes tiny.timsen, tiny.runs and tiny.expected. Rerun after changing the table format or the model.
"""

import gzip
import sys
import tempfile
from pathlib import Path
from unittest import mock

from . import crosscheck, paths, table, train
from .model import Model

OUT = Path(__file__).resolve().parent.parent / "crates" / "timsen" / "tests" / "fixtures"
# Made up for the fixture; covers context choices, new tone placement (hoà, thuỷ, khoẻ), qu/gi
# clusters, unmarked and unknown words.
CORPUS = [
    "tôi gõ phím rất nhanh",
    "bàn phím này gõ rất êm",
    "cái bàn bằng gỗ lim",
    "nhà ta có gỗ quý",
    "người ta có gõ cửa",
    "hoà bình và thuỷ lợi",
    "chúc anh khoẻ mạnh",
    "quý khách vui lòng chờ",
    "gia đình tôi ở hà nội",
    "mở file code ra xem",
    # gõ is likelier after "bạn thích", but only gỗ ends a run: an open run and an ended one differ.
    "bạn thích gỗ",
    "bạn thích gõ phím",
    "bạn thích gõ phím",
] * 6
TEST = [
    "Tôi gõ phím rất nhanh, bàn phím này gõ rất êm.",
    "Nhà ta có gỗ quý; người ta có gõ cửa.",
    "Hoà bình và thuỷ lợi. Chúc anh khoẻ mạnh!",
    "Quý khách vui lòng chờ, gia đình tôi ở Hà Nội.",
    "Mở file code ra xem commit mới.",
    "gõ",
    "Bạn thích gỗ.",
]


def build(out):
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with gzip.open(tmp / "tiny.txt.gz", "wt", encoding="utf-8") as f:
            f.write("\n".join(CORPUS) + "\n")
        argv = ["train", str(tmp / "tiny.npz"), "tiny"]
        with mock.patch.object(paths, "DATA", tmp), mock.patch.object(sys, "argv", argv):
            with mock.patch.object(train, "WORKERS", 1):
                train.main()
        table.write(Model(tmp / "tiny.npz"), out / "tiny.timsen")
        (tmp / "test").write_text("\n".join(TEST) + "\n", encoding="utf-8")
        crosscheck.write(out / "tiny.timsen", tmp / "test", out / "tiny.runs", out / "tiny.expected")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
