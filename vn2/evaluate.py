"""Forecast backtests on past weeks only (hard rule H4).

For every cutoff week we forecast the next weeks from the history up to the cutoff, and compare
with what was then sold. Two horizons matter (SupChains):
- lag 1: the first week after the cutoff;
- cumulative 3 weeks: the risk horizon of an order (lead time 2 + review period 1).
Weeks out of stock have no observable demand and are skipped. All variants are scored on the
same cells, so the comparison is fair.
"""
import pandas as pd

from vn2 import config
from vn2.baseline import seasonal_moving_average
from vn2.data import as_of, cut
from vn2.guards import require_history_only
from vn2.metrics import accuracy

HORIZON = 3


def backtest_cutoffs(first, horizon=HORIZON):
    """Every week from `first` whose next `horizon` weeks are still history (up to week 0)."""
    last = config.LAST_HISTORY_WEEK - pd.Timedelta(weeks=horizon)
    return pd.date_range(first, last, freq="W-MON")


def forecast_backtest(cleaners, cutoffs, horizon=HORIZON):
    """Lag-1 and cumulative accuracy of the benchmark forecast fed by each cleaning variant.

    `cleaners` maps a name to a function History -> demand table. Returns one row per variant.
    """
    end = cutoffs[-1] + pd.Timedelta(weeks=horizon)
    require_history_only(end)
    full = as_of(end)
    observed = full.sales.where(full.in_stock)  # demand we can observe: in-stock weeks

    collected = {name: {"lag1": [], "cum": []} for name in cleaners}
    actual = {"lag1": [], "cum": []}
    for cutoff in cutoffs:
        past = cut(full, cutoff)
        weeks = observed.columns[len(past.sales.columns):][:horizon]
        actual["lag1"].append(observed[weeks[0]])
        actual["cum"].append(observed[weeks].sum(axis=1, skipna=False))
        for name, clean in cleaners.items():
            forecast = seasonal_moving_average(clean(past), horizon)
            collected[name]["lag1"].append(forecast.iloc[:, 0])
            collected[name]["cum"].append(forecast.sum(axis=1, skipna=False))
    return _score(collected, actual)


def _score(collected, actual):
    """Accuracy per variant and horizon, on the cells where every variant has a forecast."""
    rows = {}
    for horizon in ("lag1", "cum"):
        truth = pd.concat(actual[horizon], axis=1)
        tables = {name: pd.concat(parts[horizon], axis=1) for name, parts in collected.items()}
        common = truth.notna()
        for table in tables.values():
            common &= table.notna()
        for name, table in tables.items():
            scores = accuracy(table.where(common), truth.where(common))
            label = "lag 1" if horizon == "lag1" else "3 weeks"
            rows.setdefault(name, {}).update({f"{k} {label}": v for k, v in scores.items()})
    return pd.DataFrame(rows).T.round(1)
