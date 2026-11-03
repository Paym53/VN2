"""Write the cleaned demand history to a CSV for the forecast model (phase 3).

Usage, from the repository root:
    python scripts/export_cleaned_demand.py

Output: data_clean/demand_clean_2024-04-08.csv, the layout of the competition files
(Store, Product, one column per week) with stock-out weeks left empty (= unknown demand).
History only: the last week is week 0, 2024-04-08.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # the repository root

from vn2 import config  # noqa: E402
from vn2.cleaning import clean_demand  # noqa: E402
from vn2.data import as_of  # noqa: E402

OUTPUT = config.REPO / "data_clean" / "demand_clean_2024-04-08.csv"


def main():
    demand = clean_demand(as_of(config.LAST_HISTORY_WEEK))
    OUTPUT.parent.mkdir(exist_ok=True)
    demand.to_csv(OUTPUT)
    print(f"Wrote {OUTPUT.relative_to(config.REPO)}: {demand.shape[0]} rows x "
          f"{demand.shape[1]} weeks, {int(demand.isna().sum().sum())} unknown weeks")


if __name__ == "__main__":
    main()
