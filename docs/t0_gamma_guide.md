# t0-gamma: how to use it for VN2, step by step

t0-gamma is an open-weights time-series foundation model by The Forecasting Company
(Apache-2.0, about 256 million parameters, 24 transformer layers). It forecasts **quantiles**
(a probabilistic forecast) zero-shot: no training on our data. It reads several series at once,
accepts missing values (NaN), past covariates and known-future covariates.

Source of this guide: the README of [tfc-t0 on GitHub](https://github.com/theforecastingcompany/tfc-t0).
The [Hugging Face model card](https://huggingface.co/theforecastingcompany/t0-gamma) and the
[paper on the t0 family](https://arxiv.org/abs/2609.24559) could not be read from the cloud
session; check them for details not covered here.

## Step 1: install

```bash
pip install "tfc-t0[torch]>=0.6.0"
```

Python 3.10 or newer. Use **0.6.0 or newer**: older releases load t0-gamma without an error
but run it with the wrong conventions, which silently degrades the forecast.
On a Mac with Apple silicon there is also `tfc-t0[mlx]`.
The docs do not say whether a GPU is needed; a 256M-parameter model on 599 short weekly series
should run on a CPU in minutes.

## Step 2: load the model

```python
from t0 import T0Forecaster

model = T0Forecaster.from_pretrained("theforecastingcompany/t0-gamma").eval()
```

The first call downloads the weights from Hugging Face.

## Step 3: prepare the history

The model takes a plain array: one row per series, one column per week, oldest week first.
For VN2 that is the sales table as of the round's cutoff, with stock-out weeks set to NaN
(SupChains: forecast demand, not supply-constrained sales).

```python
history = sales.where(in_stock)                 # out-of-stock week -> NaN (demand unknown)
context = history.to_numpy(dtype="float32")     # shape (599, number of weeks)
```

## Step 4: forecast quantiles

```python
LEVELS = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.833, 0.9, 0.95, 0.99]

out = model.predict(
    context,
    horizon=4,                    # weeks k, k+1, k+2, k+3 of round k
    quantile_levels=LEVELS,
    trim_leading_missing=True,    # ignore the weeks before a row has any data
    symmetric_averaging=True,     # one of the settings behind the published scores
    clip_nonnegative=True,        # demand is never negative
)
out.quantiles   # shape (599, 4, len(LEVELS)): row x week ahead x quantile level
out.median      # shape (599, 4)
```

The model was trained on 21 quantile levels from 0.01 to 0.99; other levels are interpolated
(and extrapolated on exponential tails beyond them). There is no mean output; we compute
what we need from the quantiles.

The fourth published setting, `snap_integers=True`, rounds forecasts when the history is whole
numbers. We test it both ways in phase 3: rounded quantiles of small numbers lose detail
that the scenarios need.

## Step 5 (optional): covariates

- **Past covariates** are extra rows of the same series in `context` (forecast together with it).
- **Known-future covariates** go in `future_covariates`, shape (series, covariates, weeks of
  context + horizon). Example for VN2: week of year, known for the past and the future.

```python
out = model.predict(context, horizon=4, quantile_levels=LEVELS,
                    future_covariates=week_of_year)   # shape (599, 1, weeks + 4)
```

Whether a covariate helps is decided by the backtest (FVA), not by intuition.

## Step 6: save with provenance

Save the quantiles together with the cutoff date, the model id and the package version
(hard rule H5 in `docs/project_plan.md`). The ordering step loads a forecast only if its cutoff
matches the round.

## What is not documented

The maximum context length, the GPU requirement, a mean forecast, and any guidance on
intermittent or weekly data. Fine-tuning is possible in principle (`forward` is the entry
point) but there is no recipe; we stay zero-shot.
