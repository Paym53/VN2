"""A tool for the no-look-ahead tests (hard rule H3): a copy of the data with the future destroyed.

If a forecast or an order changes when every week after the cutoff is replaced by garbage,
it used information from the future. Every policy we build is run through this check.
"""
import shutil

import numpy as np
import pandas as pd

INDEX = ["Store", "Product"]


def copy_with_garbage_future(data_dir, target_dir, cutoff, seed=0):
    """Copy the data folder, replacing every value of every week after `cutoff` by garbage.

    Sales after the cutoff become random large numbers and in-stock flags are flipped, in
    every file that holds weekly columns. Weeks up to the cutoff are copied unchanged.
    """
    rng = np.random.default_rng(seed)
    shutil.copytree(data_dir, target_dir)
    for path in target_dir.glob("*.csv"):
        table = pd.read_csv(path)
        future = [c for c in table.columns if _is_week(c) and pd.Timestamp(c) > cutoff]
        if not future:
            continue
        if table[future].dtypes.eq(bool).all():
            table[future] = ~table[future]
        else:
            table[future] = rng.integers(1_000, 9_999, size=(len(table), len(future))).astype(float)
        table.to_csv(path, index=False)
    return target_dir


def _is_week(column):
    """Week columns are labelled with their Monday date, e.g. '2024-04-08'."""
    try:
        pd.Timestamp(column)
    except ValueError:
        return False
    return column[:2] == "20"
