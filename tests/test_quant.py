import numpy as np

from research.quant import rounded


def test_zero_bits_leaves_counts_exact():
    counts = np.array([1.0, 7.0, 123456.0])
    assert rounded(counts, 0, 1e6) is counts


def test_rounding_keeps_the_ends_and_the_order():
    counts = np.array([1.0, 2.0, 50.0, 4000.0, 1e6])
    out = rounded(counts, 8, 1e6)
    assert out[0] == 1.0 and np.isclose(out[-1], 1e6)
    assert (np.diff(out) > 0).all()
    assert len(np.unique(rounded(np.arange(1.0, 100000.0), 4, 1e6))) <= 16
