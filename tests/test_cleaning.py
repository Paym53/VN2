"""Phase 1 acceptance: the cleaning rules, written as Given / When / Then scenarios."""
import numpy as np
import pandas as pd
import pytest

from tests.lookahead import copy_with_garbage_future
from vn2 import config
from vn2.cleaning import clean_demand, cleaning_summary, launched
from vn2.data import History, as_of

WEEKS = ["2024-03-04", "2024-03-11", "2024-03-18", "2024-03-25"]


def tiny_history(sales, in_stock):
    """A one-row history for readable scenarios."""
    index = pd.MultiIndex.from_tuples([(0, 1)], names=["Store", "Product"])
    return History(pd.Timestamp(WEEKS[-1]), pd.DataFrame([sales], index=index, columns=WEEKS),
                   pd.DataFrame([in_stock], index=index, columns=WEEKS), pd.DataFrame())


def test_a_stock_out_week_does_not_count_as_demand():
    # Given a row out of stock in week 2
    history = tiny_history([3.0, 0.0, 2.0, 1.0], [True, False, True, True])
    # When the history is cleaned
    demand = clean_demand(history)
    # Then week 2 is missing and the other weeks keep their sales
    assert np.isnan(demand.iloc[0, 1])
    assert demand.iloc[0, [0, 2, 3]].tolist() == [3.0, 2.0, 1.0]


def test_a_zero_sale_week_in_stock_is_real_zero_demand():
    history = tiny_history([2.0, 0.0, 0.0, 1.0], [True, True, True, True])
    assert clean_demand(history).iloc[0].tolist() == [2.0, 0.0, 0.0, 1.0]


def test_large_weeks_are_never_trimmed():
    history = tiny_history([1.0, 500.0, 1.0, 1.0], [True, True, True, True])
    assert clean_demand(history).iloc[0, 1] == 500.0


def test_pre_launch_weeks_are_missing_only_when_asked():
    # Given a row that first sold in week 3, in stock (but unsold) in week 2
    history = tiny_history([0.0, 0.0, 4.0, 0.0], [False, True, True, True])
    assert clean_demand(history).iloc[0].tolist()[1:] == [0.0, 4.0, 0.0]
    with_rule = clean_demand(history, pre_launch_missing=True).iloc[0]
    assert with_rule.isna().tolist() == [True, True, False, False]
    assert launched(history.sales).iloc[0].tolist() == [False, False, True, True]


@pytest.mark.parametrize("pre_launch_missing", [False, True])
def test_cleaning_never_looks_ahead(pre_launch_missing, tmp_path):
    cutoff = pd.Timestamp("2023-06-05")
    garbage = copy_with_garbage_future(config.DATA_DIR, tmp_path / "Data", cutoff)
    real = clean_demand(as_of(cutoff), pre_launch_missing)
    faked = clean_demand(as_of(cutoff, garbage), pre_launch_missing)
    pd.testing.assert_frame_equal(real, faked)


def test_the_summary_counts_the_real_data():
    summary = cleaning_summary(as_of(config.LAST_HISTORY_WEEK))
    assert summary["cells"] == 599 * 157
    assert summary["stock-out weeks"] == 10_517
    assert summary["pre-launch weeks"] == 7_134
    assert summary["pre-launch weeks flagged in stock"] == 629
