"""H6: orders pass the official checks. H10: scores are shown beside benchmark and winner."""
import numpy as np
import pytest

from vn2 import config
from vn2.orders import validate
from vn2.report import score_report
from vn2_simulate import OrderError, read_table

INDEX = read_table(config.DATA_DIR / "Week 0 - Submission Template.csv").index


def test_a_valid_order_passes():
    orders = validate(np.arange(len(INDEX)), INDEX)
    assert orders.dtype.kind == "i" and orders.index.equals(INDEX)


@pytest.mark.parametrize("bad", [
    np.full(len(INDEX), -1),          # negative
    np.full(len(INDEX), 0.5),         # decimals
    np.zeros(len(INDEX) - 1),         # a row missing
    np.full(len(INDEX), np.nan),      # empty cells
])
def test_invalid_orders_are_refused(bad):
    with pytest.raises(OrderError):
        validate(bad, INDEX)


def test_a_score_report_names_the_benchmark_and_the_winner():
    text = score_report(4000.0)
    assert "4,334.0" in text and "3,763.2" in text
    assert "334.0 EUR (7.7%) below" in text      # below the benchmark
    assert "236.8 EUR (6.3%) above" in text      # above the winner


def test_a_score_equal_to_the_benchmark_says_so():
    assert "equal" in score_report(config.BENCHMARK_SCORE)
