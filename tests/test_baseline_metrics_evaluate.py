"""The benchmark forecast copy, the accuracy metrics and the forecast backtest."""
import numpy as np
import pandas as pd
import pytest

from vn2 import config
from vn2.baseline import seasonal_factors, seasonal_moving_average
from vn2.cleaning import clean_demand
from vn2.data import as_of, cut
from vn2.evaluate import backtest_cutoffs, forecast_backtest
from vn2.guards import LookAheadError
from vn2.metrics import accuracy
from vn2_benchmark import policy as benchmark_policy
from vn2_simulate import read_table

STATE = read_table(config.DATA_DIR / "Week 0 - 2024-04-08 - Initial State.csv")


@pytest.mark.parametrize("cutoff", ["2023-04-10", "2024-04-08"])
def test_our_forecast_gives_exactly_the_benchmark_orders(cutoff):
    history = as_of(cutoff)
    forecast = seasonal_moving_average(clean_demand(history), horizon=4)
    position = STATE[["In Transit W+1", "In Transit W+2", "End Inventory"]].sum(axis=1)
    ours = (forecast.sum(axis=1) - position).clip(lower=0).round(0).astype(int)
    official = benchmark_policy(history.sales, history.in_stock, history.master, STATE)
    assert (ours.values == official.values).all()


def test_seasonal_factors_average_one():
    factors = seasonal_factors(clean_demand(as_of(config.LAST_HISTORY_WEEK)))
    assert len(factors) == 52 and factors.mean() == pytest.approx(1.0)


def test_accuracy_on_a_worked_example():
    forecast = pd.DataFrame([[12.0, 8.0], [5.0, np.nan]])
    actual = pd.DataFrame([[10.0, 10.0], [np.nan, 3.0]])  # only the first row is comparable
    scores = accuracy(forecast, actual)
    assert scores["MAE%"] == pytest.approx(20.0)  # (2 + 2) / 20
    assert scores["Bias%"] == pytest.approx(0.0)
    assert scores["Score%"] == pytest.approx(20.0)
    biased = accuracy(forecast + 1, actual)
    assert biased["Bias%"] == pytest.approx(10.0) and biased["Score%"] == pytest.approx(30.0)
    # Under-forecasting must not lower the Score: the bias counts as an absolute value.
    low = accuracy(forecast - 1, actual)
    assert low["Bias%"] == pytest.approx(-10.0) and low["Score%"] == pytest.approx(30.0)


def test_cut_equals_reading_at_that_cutoff():
    full = as_of(config.LAST_HISTORY_WEEK)
    early, direct = cut(full, "2023-06-05"), as_of("2023-06-05")
    pd.testing.assert_frame_equal(early.sales, direct.sales)
    pd.testing.assert_frame_equal(early.in_stock, direct.in_stock)
    with pytest.raises(ValueError):
        cut(full, "2023-06-06")


def test_backtest_cutoffs_stop_before_the_test_weeks():
    cutoffs = backtest_cutoffs("2023-04-10")
    assert cutoffs[-1] + pd.Timedelta(weeks=3) == config.LAST_HISTORY_WEEK


def test_a_backtest_reaching_into_test_weeks_is_refused():
    with pytest.raises(LookAheadError):
        forecast_backtest({"B": clean_demand}, pd.DatetimeIndex(["2024-04-01"]))


def test_identical_variants_score_identically_on_the_same_cells():
    cutoffs = backtest_cutoffs("2024-02-05")
    table = forecast_backtest({"one": clean_demand, "two": clean_demand,
                               "raw": lambda history: history.sales}, cutoffs)
    assert table.loc["one"].equals(table.loc["two"])
    assert list(table.columns)[:3] == ["MAE% lag 1", "Bias% lag 1", "Score% lag 1"]
    assert table.loc["raw", "Bias% lag 1"] < table.loc["one", "Bias% lag 1"]
