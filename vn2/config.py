"""Fixed facts of the VN2 game, kept in one place."""
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
DATA_DIR = REPO / "Data"
RESULTS_DIR = REPO / "results"

# Week 0 is the last week of history known before round 1. Weeks 1 to 8 are the final exam:
# no tuning, model choice or analysis may look at them (hard rules H3 and H4).
LAST_HISTORY_WEEK = pd.Timestamp("2024-04-08")
FIRST_TEST_WEEK = LAST_HISTORY_WEEK + pd.Timedelta(weeks=1)

# Before round k the competitors knew the sales up to week k-1; round 6 is the last round.
LAST_ROUND = 6
LAST_KNOWN_WEEK = LAST_ROUND - 1

# Reference results, printed beside every score (hard rule H10).
SETUP_COST = 913.8
BENCHMARK_SCORE = 4334.0
WINNER_SCORE = 3763.2
