"""The only door to the competition data (hard rule H3).

Every reader in the project calls `as_of(cutoff)`. It returns the sales and in-stock flags of
the weeks up to the cutoff and nothing later, exactly what a planner knew at that time.
"""
from dataclasses import dataclass

import pandas as pd

from vn2 import config
from vn2.guards import LookAheadError
from vn2_simulate import read_table, sales_file, week_date


@dataclass(frozen=True)
class History:
    """What a planner knows at a cutoff week. One row per Store x Product, one column per week."""

    cutoff: pd.Timestamp
    sales: pd.DataFrame  # units sold per week, oldest week first
    in_stock: pd.DataFrame  # True when stock was left at the end of the week
    master: pd.DataFrame  # product and store hierarchy (no weeks in it)


def week_number(cutoff):
    """Weeks after week 0 (2024-04-08): 0 for week 0, k for week k, negative before it."""
    weeks = (pd.Timestamp(cutoff) - config.LAST_HISTORY_WEEK) / pd.Timedelta(weeks=1)
    if weeks != int(weeks):
        raise ValueError(f"{cutoff} is not a Monday of the data (weeks start on Mondays).")
    return int(weeks)


def as_of(cutoff, data_dir=config.DATA_DIR):
    """The history known at the end of the week `cutoff`.

    Before round k the cutoff is week k-1, read from that week's sales file, as in the
    competition. A cutoff after week 5 is refused: no round ever knew those weeks.
    """
    cutoff = pd.Timestamp(cutoff)
    week = week_number(cutoff)
    if week > config.LAST_KNOWN_WEEK:
        raise LookAheadError(f"No round ever knew the sales of {cutoff.date()}.")

    sales = read_table(sales_file(max(week, 0), data_dir))
    in_stock = read_table(data_dir / "Week 0 - In Stock.csv")
    master = read_table(data_dir / "Week 0 - Master.csv")

    known_weeks = [column for column in sales.columns if pd.Timestamp(column) <= cutoff]
    if not known_weeks or known_weeks[-1] != cutoff.strftime("%Y-%m-%d"):
        raise ValueError(f"{cutoff.date()} is not a week of the data.")
    return History(cutoff, sales[known_weeks], in_stock[known_weeks].astype(bool), master)


def cut(history, cutoff):
    """The same history, ending at an earlier cutoff (for backtests over many cutoffs)."""
    cutoff = pd.Timestamp(cutoff)
    weeks = [column for column in history.sales.columns if pd.Timestamp(column) <= cutoff]
    if not weeks or weeks[-1] != cutoff.strftime("%Y-%m-%d"):
        raise ValueError(f"{cutoff.date()} is not a week of this history.")
    return History(cutoff, history.sales[weeks], history.in_stock[weeks], history.master)


def round_cutoff(round_number):
    """The last week known before round k (k = 1 to 6): week k-1."""
    if not 1 <= round_number <= config.LAST_ROUND:
        raise ValueError(f"Rounds run from 1 to {config.LAST_ROUND}, not {round_number}.")
    return pd.Timestamp(week_date(round_number - 1))
