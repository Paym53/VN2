"""Turn recorded sales into demand history (phase 1).

Simple, global rules only (SupChains: clean the data, bypass the periods you cannot observe,
never trim outliers):

1. Stock-out week -> missing. When the in-stock flag is False the shelf was empty all week
   (sales are always 0 then) and the real demand is unknown. We do not guess it; the forecast
   skips the week. Backtest (scripts/cleaning_fva.py): bias -9.7 % -> +0.3 %, Score -8.6 points.
2. Optional: weeks before a row's first sale -> missing (product not on sale yet). Neutral for
   the 13-week benchmark forecast (+0.6 / -0.2 Score points); off by default until the t0-gamma
   backtest of phase 3 decides.

Everything else stays as recorded: zero-sale weeks in stock are real zero demand, and large
weeks are real sales.
"""
import numpy as np
import pandas as pd


def launched(sales):
    """True from the week of a row's first sale onwards (that week included)."""
    return (sales > 0).cummax(axis=1)


def clean_demand(history, pre_launch_missing=False):
    """Demand history at the cutoff: sales, with unobservable weeks set to NaN.

    `history` comes from vn2.data.as_of, so it holds no week after the cutoff.
    """
    observable = history.in_stock
    if pre_launch_missing:
        observable = observable & launched(history.sales)
    return history.sales.where(observable, np.nan)


def cleaning_summary(history):
    """How many cells each rule concerns, as a small table."""
    sales, in_stock = history.sales, history.in_stock
    pre_launch = ~launched(sales)
    return pd.Series({
        "cells": sales.size,
        "stock-out weeks": int((~in_stock).values.sum()),
        "pre-launch weeks": int(pre_launch.values.sum()),
        "pre-launch weeks flagged in stock": int((pre_launch & in_stock).values.sum()),
    })
