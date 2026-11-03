"""Guards that stop the model from looking at data it may not use (hard rules H3 and H4)."""
import pandas as pd

from vn2 import config


class LookAheadError(Exception):
    """Raised when code asks for data it would not have had at that time."""


def require_history_only(last_week):
    """Tuning, backtests and model choice may only use weeks up to week 0 (2024-04-08).

    Call this with the last week a backtest or analysis touches. Weeks 1 to 8 are the final
    exam: looking at them while building the model would make the final score meaningless.
    """
    last_week = pd.Timestamp(last_week)
    if last_week > config.LAST_HISTORY_WEEK:
        raise LookAheadError(
            f"{last_week.date()} is a test week. Tuning and backtests must end on or before "
            f"{config.LAST_HISTORY_WEEK.date()}."
        )


def git_tree_is_clean(porcelain_status):
    """True when `git status --porcelain` printed nothing: every change is committed.

    The final score may only be computed from committed code, so that every final run can
    be traced to one commit (hard rule H4).
    """
    return porcelain_status.strip() == ""
