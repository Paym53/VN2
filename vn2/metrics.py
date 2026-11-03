"""Forecast accuracy, the SupChains way: MAE%, Bias% and Score = MAE% + |Bias%|. Never MAPE.

All three are scaled by total demand, so large rows weigh more than tiny ones and weeks with
zero demand cause no division by zero.
"""
import pandas as pd


def accuracy(forecast, actual):
    """MAE%, Bias% and Score of forecasts against actual demand (same shape, NaN = skip)."""
    keep = forecast.notna() & actual.notna()
    error = (forecast - actual)[keep]
    total = actual[keep].sum().sum()
    mae = error.abs().sum().sum() / total
    bias = error.sum().sum() / total
    return pd.Series({"MAE%": 100 * mae, "Bias%": 100 * bias, "Score%": 100 * (mae + abs(bias))})
