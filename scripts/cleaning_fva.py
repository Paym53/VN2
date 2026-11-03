"""Phase 1: does our cleaning make the benchmark forecast better? (Forecast Value Added)

Usage, from the repository root:
    python scripts/cleaning_fva.py

Compares three versions of the same forecast (the competition benchmark's seasonal moving
average), fed with three versions of the history, over many past cutoffs. History only:
the last week used is 2024-04-08.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # the repository root

from vn2.cleaning import clean_demand  # noqa: E402
from vn2.evaluate import backtest_cutoffs, forecast_backtest  # noqa: E402

CLEANERS = {
    "A raw sales": lambda history: history.sales,
    "B stock-outs missing (benchmark)": clean_demand,
    "C + pre-launch missing": lambda history: clean_demand(history, pre_launch_missing=True),
}


def main():
    for label, first in [("Two years of cutoffs (2022-04-11 to 2024-03-18)", "2022-04-11"),
                         ("Last year only (2023-04-10 to 2024-03-18)", "2023-04-10")]:
        cutoffs = backtest_cutoffs(first)
        print(f"\n{label}: {len(cutoffs)} cutoffs, all 599 rows")
        print(forecast_backtest(CLEANERS, cutoffs).to_string())


if __name__ == "__main__":
    main()
