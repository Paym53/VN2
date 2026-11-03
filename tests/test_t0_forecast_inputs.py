"""What t0-gamma receives: the right cleaned history, cut at each cutoff (hard rules H3 and H5).

t0-gamma itself cannot run in CI (model download), so a stand-in model records its inputs.
"""
import numpy as np
import pandas as pd
import pytest

from forecasting import t0_forecast as t0f
from vn2 import config
from vn2.cleaning import clean_demand
from vn2.data import as_of


@pytest.fixture(scope="module")
def demand():
    return t0f.read_demand()


def test_the_csv_is_the_cleaned_history_up_to_week_0(demand):
    expected = clean_demand(as_of(config.LAST_HISTORY_WEEK)).astype("float32")
    pd.testing.assert_frame_equal(demand, expected, check_names=False)
    assert demand.columns[-1] == "2024-04-08"


def test_the_pre_launch_variant_matches_the_cleaning_rule(demand):
    expected = clean_demand(as_of(config.LAST_HISTORY_WEEK), pre_launch_missing=True)
    pd.testing.assert_frame_equal(t0f.pre_launch_missing(demand), expected.astype("float32"),
                                  check_names=False)


def test_cutoffs(demand):
    cutoffs = t0f.make_cutoffs(list(demand.columns))
    assert len(cutoffs) == 103
    assert cutoffs[0] == "2022-04-11" and cutoffs[-2:] == ["2024-03-18", "2024-04-08"]
    assert len(t0f.make_cutoffs(list(demand.columns), every=13)) == 9


def test_the_context_ends_at_the_cutoff_and_ignores_later_weeks(demand):
    cutoff = "2023-06-05"
    garbage = demand.copy()
    later = [week for week in demand.columns if week > cutoff]
    garbage[later] = 9_999.0
    context = t0f.context_at(demand, cutoff)
    np.testing.assert_array_equal(context, t0f.context_at(garbage, cutoff))
    assert context.shape == (599, list(demand.columns).index(cutoff) + 1)


def test_quantile_levels_are_valid_for_t0():
    levels = np.array(t0f.LEVELS)
    assert (np.diff(levels) > 0).all() and levels.min() > 0 and levels.max() < 1
    assert 0.8333 in t0f.LEVELS and len(levels) == 22


def test_week_of_year_repeats_every_year():
    calendar = t0f.week_of_year("2023-01-02", 105)
    assert calendar.shape == (2, 105)
    np.testing.assert_allclose(calendar[:, 0], calendar[:, 52], atol=0.05)


class FakeQuantiles:
    """Mimics a torch tensor: .float().cpu().numpy()."""

    def __init__(self, array):
        self.array = array

    def float(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.array


class RecordingModel:
    """Stands in for t0-gamma: remembers the inputs, returns constant quantiles."""

    def predict(self, context, **settings):
        self.context, self.settings = context, settings
        shape = (len(context), settings["horizon"], len(settings["quantile_levels"]))
        return type("Out", (), {"quantiles": FakeQuantiles(np.ones(shape, np.float32))})


@pytest.mark.parametrize("use_week_of_year", [False, True])
def test_forecast_cutoff_feeds_only_known_weeks(demand, use_week_of_year):
    model, cutoff = RecordingModel(), "2022-04-11"
    result = t0f.forecast_cutoff(model, demand, cutoff, use_week_of_year)
    weeks_known = list(demand.columns).index(cutoff) + 1
    assert model.context.shape[1] == weeks_known
    assert result.shape == (599, t0f.HORIZON, len(t0f.LEVELS))
    never_seen = np.isnan(t0f.context_at(demand, cutoff)).all(axis=1)
    assert np.isnan(result[never_seen]).all() and not np.isnan(result[~never_seen]).any()
    assert model.settings["trim_leading_missing"] and model.settings["clip_nonnegative"]
    if use_week_of_year:
        covariates = model.settings["future_covariates"]
        assert covariates.shape == (len(model.context), 2, weeks_known + t0f.HORIZON)
