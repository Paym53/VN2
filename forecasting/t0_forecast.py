"""Probabilistic demand forecasts for VN2 with t0-gamma. Runs on your own machine.

What it does
    For every cutoff week (a week we pretend is "today"), it gives t0-gamma the cleaned demand
    of the weeks up to that cutoff, and nothing later, and asks for 22 quantiles of the demand
    of the next 4 weeks, for all 599 rows. It saves everything to one .npz file.

Setup, once (Python 3.10 or newer):
    python -m venv .venv
    source .venv/bin/activate              # Windows: .venv\\Scripts\\activate
    pip install "tfc-t0[torch]>=0.6.0" pandas numpy

Run, from the repository root:
    python forecasting/t0_forecast.py --every 13            # quick test: 9 cutoffs
    python forecasting/t0_forecast.py                       # main run: 103 weekly cutoffs
    python forecasting/t0_forecast.py --pre-launch-missing  # variant: pre-launch weeks unknown
    python forecasting/t0_forecast.py --week-of-year        # variant: calendar as known input
    Add --device cuda (NVIDIA GPU) or --device mps (Apple GPU) if you have one; CPU works too.

Output
    forecasts/t0_<variant>.npz. Send these files back; the accuracy check (Forecast Value Added
    against the benchmark) is done in the repository.
"""
import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
DEMAND_CSV = REPO / "data_clean" / "demand_clean_2024-04-08.csv"
OUT_DIR = REPO / "forecasts"
MODEL_ID = "theforecastingcompany/t0-gamma"

HORIZON = 4  # after a cutoff: the two weeks before an order arrives, its arrival week, one more
FIRST_CUTOFF = "2022-04-11"  # one full year of history before the first forecast
BACKTEST_GAP = 3  # backtest cutoffs stop 3 weeks before the last week, so actuals exist

# The 21 levels t0 was trained on, plus 0.8333 = 1 / (1 + 0.2): VN2's cost-optimal quantile.
LEVELS = [0.01, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65,
          0.7, 0.75, 0.8, 0.8333, 0.85, 0.9, 0.95, 0.99]


def read_demand(path=DEMAND_CSV):
    """The cleaned demand: one row per Store x Product, one column per week, NaN = unknown."""
    return pd.read_csv(path).set_index(["Store", "Product"]).astype("float32")


def pre_launch_missing(demand):
    """Variant: the weeks before a row's first sale become unknown too."""
    launched = (demand.fillna(0) > 0).cummax(axis=1)
    return demand.where(launched)


def make_cutoffs(weeks, every=1):
    """Backtest cutoffs every `every` weeks, plus the last week (the forecast for round 1)."""
    last = pd.Timestamp(weeks[-1])
    backtest = pd.date_range(FIRST_CUTOFF, last - pd.Timedelta(weeks=BACKTEST_GAP),
                             freq=f"{7 * every}D")
    return [d.strftime("%Y-%m-%d") for d in backtest] + [weeks[-1]]


def context_at(demand, cutoff):
    """The demand of the weeks up to and including the cutoff: what was known then."""
    known = [week for week in demand.columns if week <= cutoff]
    return demand[known].to_numpy(dtype=np.float32)


def week_of_year(first_week, length):
    """Known-future calendar input: sine and cosine of the week of the year, shape (2, length)."""
    weeks = pd.date_range(first_week, periods=length, freq="7D")
    angle = 2 * np.pi * weeks.isocalendar().week.to_numpy(dtype=np.float32) / 52.18
    return np.stack([np.sin(angle), np.cos(angle)]).astype(np.float32)


def load_model(device):
    """Download (first time only) and load t0-gamma; check the package is recent enough."""
    import torch  # noqa: F401  (needed by the torch backend)
    from t0 import T0Forecaster

    installed = tuple(int(n) for n in re.findall(r"\d+", version("tfc-t0"))[:3])
    if installed < (0, 6, 0):
        raise SystemExit("Install tfc-t0 0.6.0 or newer: older releases run t0-gamma wrongly.")
    return T0Forecaster.from_pretrained(MODEL_ID).eval().to(device)


def forecast_cutoff(model, demand, cutoff, use_week_of_year):
    """Quantile forecasts after one cutoff, shape (rows, HORIZON, len(LEVELS)).

    Rows with no observation at all yet (not launched) get NaN: there is nothing to forecast from.
    """
    past = context_at(demand, cutoff)
    seen = ~np.isnan(past).all(axis=1)
    settings = dict(horizon=HORIZON, quantile_levels=LEVELS, trim_leading_missing=True,
                    symmetric_averaging=True, clip_nonnegative=True, snap_integers=False)
    if use_week_of_year:
        calendar = week_of_year(demand.columns[0], past.shape[1] + HORIZON)
        settings["future_covariates"] = np.repeat(calendar[None], seen.sum(), axis=0)

    result = np.full((len(past), HORIZON, len(LEVELS)), np.nan, dtype=np.float32)
    quantiles = model.predict(past[seen], **settings).quantiles
    result[seen] = quantiles.float().cpu().numpy()
    return result


def save(path, quantiles, demand, cutoffs, args):
    """One file with the forecasts and their provenance (hard rule H5)."""
    provenance = {
        "model": MODEL_ID, "package": f"tfc-t0 {version('tfc-t0')}",
        "input": DEMAND_CSV.name,
        "input_sha256": hashlib.sha256(DEMAND_CSV.read_bytes()).hexdigest(),
        "pre_launch_missing": args.pre_launch_missing, "week_of_year": args.week_of_year,
        "horizon": HORIZON, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    np.savez_compressed(path, quantiles=quantiles, levels=np.array(LEVELS),
                        cutoffs=np.array(cutoffs), stores=demand.index.get_level_values(0).values,
                        products=demand.index.get_level_values(1).values,
                        provenance=json.dumps(provenance))


def main():
    parser = argparse.ArgumentParser(description="t0-gamma quantile forecasts for VN2")
    parser.add_argument("--every", type=int, default=1, help="weeks between backtest cutoffs")
    parser.add_argument("--pre-launch-missing", action="store_true")
    parser.add_argument("--week-of-year", action="store_true")
    parser.add_argument("--device", default="cpu", help="cpu, cuda or mps")
    args = parser.parse_args()

    demand = read_demand()
    if args.pre_launch_missing:
        demand = pre_launch_missing(demand)
    cutoffs = make_cutoffs(list(demand.columns), args.every)
    model = load_model(args.device)

    start, results = time.time(), []
    for i, cutoff in enumerate(cutoffs, start=1):
        results.append(forecast_cutoff(model, demand, cutoff, args.week_of_year))
        print(f"  {i:3d}/{len(cutoffs)}  cutoff {cutoff}  ({time.time() - start:5.0f} s)")

    variant = "base" + "_prelaunch" * args.pre_launch_missing + "_woy" * args.week_of_year
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f"t0_{variant}.npz"
    save(path, np.stack(results), demand, cutoffs, args)

    median = results[-1][:, 0, LEVELS.index(0.5)]
    print(f"\nSaved {path}  ({path.stat().st_size / 1e6:.1f} MB)")
    print(f"Check: total median forecast for the week after {cutoffs[-1]}: {np.nansum(median):.0f}"
          f" units; mean weekly demand of the last 13 weeks: "
          f"{demand.iloc[:, -13:].mean(axis=1).sum():.0f} units")


if __name__ == "__main__":
    main()
