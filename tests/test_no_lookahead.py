"""H3: nothing we compute for a cutoff week may depend on data after that week."""
import pandas as pd
import pytest

from tests.lookahead import copy_with_garbage_future
from vn2 import config
from vn2.data import as_of, round_cutoff, week_number
from vn2.guards import LookAheadError
from vn2_benchmark import policy as benchmark_policy
from vn2_simulate import read_table

INITIAL_STATE = read_table(config.DATA_DIR / "Week 0 - 2024-04-08 - Initial State.csv")

# A backtest week a year before the test, week 0, and the cutoffs of rounds 1, 4 and 6.
CUTOFFS = ["2023-04-10", "2024-04-08", round_cutoff(1), round_cutoff(4), round_cutoff(6)]

# Every ordering policy we build is added here and must pass the same check.
POLICIES = {"benchmark": benchmark_policy}


@pytest.mark.parametrize("cutoff", CUTOFFS)
def test_as_of_ends_exactly_at_the_cutoff(cutoff):
    history = as_of(cutoff)
    assert history.sales.columns[-1] == pd.Timestamp(cutoff).strftime("%Y-%m-%d")
    assert list(history.in_stock.columns) == list(history.sales.columns)
    assert history.in_stock.dtypes.eq(bool).all()


@pytest.mark.parametrize("cutoff", CUTOFFS)
def test_garbage_after_the_cutoff_changes_nothing(cutoff, tmp_path):
    garbage = copy_with_garbage_future(config.DATA_DIR, tmp_path / "Data", pd.Timestamp(cutoff))
    real, faked = as_of(cutoff), as_of(cutoff, garbage)
    pd.testing.assert_frame_equal(real.sales, faked.sales)
    pd.testing.assert_frame_equal(real.in_stock, faked.in_stock)
    for name, policy in POLICIES.items():
        orders_real = policy(real.sales, real.in_stock, real.master, INITIAL_STATE)
        orders_faked = policy(faked.sales, faked.in_stock, faked.master, INITIAL_STATE)
        pd.testing.assert_series_equal(orders_real, orders_faked, obj=f"orders of {name}")


def test_the_garbage_copy_really_destroys_the_future(tmp_path):
    """Guards the guard: the check above would pass trivially if nothing was changed."""
    cutoff = pd.Timestamp("2023-04-10")
    garbage = copy_with_garbage_future(config.DATA_DIR, tmp_path / "Data", cutoff)
    later = as_of("2023-04-17", garbage).sales["2023-04-17"]
    assert (later >= 1_000).all()


def test_no_round_knows_the_weeks_after_week_5():
    with pytest.raises(LookAheadError):
        as_of(round_cutoff(6) + pd.Timedelta(weeks=1))


def test_a_date_that_is_not_a_week_of_the_data_is_refused():
    with pytest.raises(ValueError):
        as_of("2024-04-09")  # a Tuesday
    with pytest.raises(ValueError):
        as_of("2015-01-05")  # a Monday before the history starts


def test_rounds_and_week_numbers():
    assert round_cutoff(1) == config.LAST_HISTORY_WEEK
    assert week_number(round_cutoff(6)) == 5
    with pytest.raises(ValueError):
        round_cutoff(7)
