"""The competition benchmark's forecast, rewritten to take any demand history.

Same method as vn2_benchmark.py (a parity test proves the orders are identical):
1. Seasonal factors: the mean demand of all rows per week, averaged per ISO week number,
   divided by the mean of these 52 numbers.
2. Level: the mean of the last 13 weeks of deseasonalised demand (missing weeks skipped).
3. Forecast: level x seasonal factor of each future week.
"""
import numpy as np
import pandas as pd

WINDOW = 13  # weeks in the moving average


def seasonal_factors(demand):
    """One multiplicative factor per ISO week number, with mean 1."""
    weekly_mean = demand.mean()  # mean over rows, per week; missing cells skipped
    iso_weeks = pd.to_datetime(demand.columns).isocalendar().week.values
    by_week = weekly_mean.groupby(iso_weeks).mean()
    return by_week / by_week.mean()


def seasonal_moving_average(demand, horizon, window=WINDOW):
    """Forecast of the `horizon` weeks after the last column of `demand` (rows x weeks)."""
    factors = seasonal_factors(demand)
    weeks = pd.to_datetime(demand.columns)
    deseasonalised = demand / factors.loc[weeks.isocalendar().week.values].values
    level = deseasonalised.iloc[:, -window:].mean(axis=1)

    future = pd.date_range(weeks[-1] + pd.Timedelta(weeks=1), periods=horizon, freq="W-MON")
    future_factors = factors.loc[future.isocalendar().week.values].values
    return pd.DataFrame(np.outer(level.values, future_factors), index=demand.index,
                        columns=future.strftime("%Y-%m-%d"))
