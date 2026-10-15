"""Where corpora, test sets and models live. Defaults to /tmp, which is RAM on the dev machine:
everything here is regenerated per experiment and gigabytes of rewrites wear out an SSD."""

import os
from pathlib import Path

ROOT = Path(os.environ.get("DOAN_DAU_DIR", "/tmp/doan-dau"))
DATA = ROOT / "data"
TEST = ROOT / "test"
MODELS = ROOT / "models"


def ensure():
    for d in (DATA, TEST, MODELS):
        d.mkdir(parents=True, exist_ok=True)
