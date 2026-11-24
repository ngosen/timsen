import numpy as np

from research.quant import dense_bytes, rounded


def test_zero_bits_leaves_counts_exact():
    counts = np.array([1.0, 7.0, 123456.0])
    assert rounded(counts, 0, 1e6) is counts


def test_rounding_keeps_the_ends_and_the_order():
    counts = np.array([1.0, 2.0, 50.0, 4000.0, 1e6])
    out = rounded(counts, 8, 1e6)
    assert out[0] == 1.0 and np.isclose(out[-1], 1e6)
    assert (np.diff(out) > 0).all()
    assert len(np.unique(rounded(np.arange(1.0, 100000.0), 4, 1e6))) <= 16


def test_dense_file_is_under_half_of_version_2_for_the_same_ngrams():
    n_words, n_bi, n_tri = 40_801, 912_919, 2_052_941
    assert dense_bytes(0, n_words, n_bi, n_tri, leftover=False) < (10 * n_bi + 6 * n_tri) / 2
    assert dense_bytes(0, n_words, n_bi, n_tri, True) - dense_bytes(0, n_words, n_bi, n_tri, False) == n_bi
