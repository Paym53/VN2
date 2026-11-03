# Project plan: VN2 with t0-gamma forecasts and the Seeker solver

Status: **proposal, waiting for approval.** Verification tier: **Tier 2** (the code decides
order quantities; see `docs/engineering_protocol.md` §6).

## 1. Formulation

**Decision.** Before each round k = 1..6, one order quantity per Store x Product row
(599 whole numbers, 0 or more). Order k arrives at the start of week k+2.

**Objective.** Minimise the official VN2 score: the cost of weeks 3 to 8 with
0.2 EUR per unit left on the shelf at the end of a week and 1 EUR per lost sale.
Reference points: benchmark 4,334.0 EUR, winner 3,763.2 EUR.

**Approach in one sentence.** Clean the history (stock-out weeks become missing values),
let **t0-gamma** produce probabilistic demand forecasts, turn them into demand scenarios,
and let **Seeker** pick the orders that minimise the expected cost, with the few policy
settings tuned by **historical simulation** on weeks before 8 April 2024.

**Hard constraints** (each one has a gate that fails the build; see §3).
**Soft objectives** (traded off inside the feasible region): simplicity and readability
(short, explained code), few tuned parameters, running time, robustness across backtest
windows rather than the best single window.

**Out of scope.** Any change to the competition rules, data or official scripts;
per-product manual adjustments; segmentation (ABC, XYZ, demand patterns); outlier trimming.

## 2. How the SupChains Way shapes the model

| SupChains principle | What we do |
|---|---|
| Forecast unconstrained demand, never supply-constrained sales | Weeks flagged out of stock become missing values (NaN) in the history; t0-gamma reads NaN as "no observation". Pre-launch weeks are trimmed. |
| Do not detect or trim outliers; fix the data, bypass exceptional periods | No statistical outlier rule anywhere. Only the stock-out flag decides what is bypassed. |
| No segmentation; one global model | One model (t0-gamma, zero-shot, global) for all 599 rows; one global set of policy parameters. |
| Benchmark everything (FVA) | Every forecast and every policy is compared with the competition benchmark (13-week seasonal moving average, 4-week coverage). A step that does not beat it is dropped. |
| Metrics: MAE%, Bias%, Score = MAE% + abs(Bias%); never MAPE | Forecast accuracy is reported with these, on lag 1 and on the cumulative risk horizon (lead time 2 + review period 1 = 3 weeks), on in-stock weeks only. |
| Outgrow the safety-stock formula: probabilistic simulation of the future | No z-sigma formula. Orders come from expected cost over demand scenarios. |
| A-tier inventory practice: inventory projection ordering + an optimisation framework | Each order projects stock through the two weeks before arrival (lost sales included) and is chosen against the cost of the arrival week. Policy settings are tuned by replaying past weeks. |
| Costs drive service, not targets | No service-level target: 1 EUR shortage vs 0.2 EUR holding enters the objective directly (critical ratio 1/1.2 = 0.83). |
| Judge over many cycles, not one lucky round | Backtests over several start dates; report mean and spread, not the best window. |

## 3. Hard rules: what the model (and Claude) may never do, and the gate that enforces it

| # | Rule | Gate (deterministic, fails CI) |
|---|---|---|
| H1 | The official files (`vn2_simulate.py`, `vn2_play.py`, `vn2_benchmark.py`, `README.md`'s rules, everything in `Data/`) are never changed. | `tests/test_official_files.py` compares SHA-256 hashes with a committed manifest. |
| H2 | The official simulator stays the referee. | Test: `vn2_play` with `vn2_benchmark.py` prints setup 913.8 and score 4,334.0. |
| H3 | **No look-ahead.** A forecast or order for round k uses only sales and in-stock flags up to week k-1. | (a) All project code reads data only through `vn2/data.py::as_of(cutoff)`, which cuts columns after the cutoff. (b) **Perturbation test:** replace every value after the cutoff with garbage; forecasts and orders must stay bit-identical. (c) Static test: no module except `scripts/final_score.py` names the Week 1-8 files or dates from 2024-04-15 on. |
| H4 | **Test-set lock.** Weeks 1-8 are the final exam, never training data. Tuning and model choice use only weeks up to 2024-04-08. | The backtest raises an error for any window that ends after 2024-04-08 (tested). `scripts/final_score.py` refuses to run on a dirty git tree and appends commit hash and score to `results/final_runs.csv`; every final run stays in that log, so results cannot be cherry-picked. |
| H5 | Forecast files carry their provenance. | Each saved forecast stores its cutoff date, model id and package version; the loader rejects a file whose cutoff does not match the round (tested). |
| H6 | Orders are valid. | Every order passes the official `check_order` (599 rows, template order, whole numbers >= 0). |
| H7 | The solver answer is checked, not trusted. | For the per-row ordering problem an exact answer exists (enumerate every quantity over the same scenarios). Test: Seeker's orders cost no more than the enumeration optimum + 0.1 %. Seeker's `test_set` checks that the cost term equals the cost formula. |
| H8 | Our fast simulator equals the official one. | Parity test: our backtest simulator and the official `play_week` give identical states on random inputs. |
| H9 | Runs are reproducible. | Fixed seeds; Seeker's deterministic mode (`minimize_det`) for every reported number; package versions pinned. |
| H10 | Honest reporting. | Every score report prints the benchmark (4,334.0) and the winner (3,763.2) beside it, plus the backtest mean and spread. |
| H11 | No secrets in the public repo. | `.gitignore` covers `*.sio` (Seeker licence); a test fails if any `*.sio` file is tracked. |

Status: H1, H2, H3, H4, H6, H10 and H11 are enforced since phase 0. H8 arrives with the
simulator (phase 2), H5 with the forecast files (phase 3), H7 and H9 with the Seeker model
(phase 4). The gate settings are themselves tested (`tests/test_gates_stay_strict.py`).

Quality gates (Tier 2): `ruff` with max complexity 10 and max 40 statements per function,
`pytest --cov-fail-under=85` on the `vn2/` package, mutation testing (`mutmut`) on the
simulator and cost functions. Seeker and t0-gamma cannot run in CI (licence, model
download), so CI tests their code paths with small stubs; the real runs happen on your
machine and their outputs come back as files.

## 4. Phases

Each phase ends with a pull request and a short verification report. No phase starts
before the previous one passed its gates.

### Phase 0: Guardrails (Claude, no licence needed)
Repository layout (`vn2/` package, `scripts/`, `tests/`), the gates H1-H11, CI on GitHub
Actions, `requirements.txt`. Nothing about forecasting yet.
*Done when:* CI is green and each gate has a test that fails when the rule is broken.

### Phase 1: Data understanding and cleaning
- Profile the data: share of stock-out weeks, pre-launch weeks, rows with very little history,
  suspicious flags (for example, in stock but zero sales for many weeks, or out of stock with
  high sales).
- Cleaning rules, all of them simple and global: stock-out week -> NaN; leading weeks before the
  first sale -> trimmed; no outlier trimming.
- Check with the benchmark first: does the benchmark get better or worse with our cleaning? (FVA)

*Acceptance (Gherkin):*
```gherkin
Scenario: A stock-out week does not count as demand
  Given a row whose in-stock flag is False in week w
  When the history is cleaned
  Then the demand of week w is missing (NaN), not the recorded sales

Scenario: Cleaning never looks ahead
  Given a cutoff week c
  When the history is cleaned as of c
  Then the result does not change if any data after c is altered
```

### Phase 2: Evaluation framework (backtest)
- A vectorised copy of the official weekly mechanics (parity test H8).
- Backtest games: the same 8-week game, started at several past dates before 2024-04-08
  (including the same season one year earlier, April-June 2023). As in the competition,
  recorded sales are the demand. All policies start from the same initial state, built by a
  short warm-up with the benchmark policy.
- Forecast metrics: MAE%, Bias%, Score on lag 1 and on the 3-week cumulative horizon,
  in-stock weeks only; pinball loss and coverage for the quantiles.
- Baseline: the competition benchmark in our backtest.

*Acceptance:* the benchmark run through our backtest framework on the real weeks 1-8 gives
4,334.0 (same mechanics as the official code).

### Phase 3: t0-gamma probabilistic forecasts (you run the script)
- One script, `scripts/run_t0.py`, forecasts all 599 rows for every cutoff we need
  (backtest cutoffs, then the six round cutoffs) and saves quantiles with provenance (H5).
- Variants, compared by FVA against the benchmark forecast: raw sales vs cleaned history;
  with and without a calendar covariate (week of year); `snap_integers` on/off.
- Calibration: is the 83 % quantile exceeded about 17 % of the time?

*Acceptance:* the chosen variant has a lower Score than the benchmark forecast on the
backtest cutoffs (lag 1 and cumulative), or we say so and keep the better one.

### Phase 4: Seeker ordering model (you run the script)
Per round, for all 599 rows at once:
1. Turn the t0 quantiles into demand scenarios for weeks k, k+1, k+2 (sampling from the
   quantile curve; the link between weeks is one parameter, tuned in phase 5).
2. Project stock through weeks k and k+1 with lost sales: start of week k+2 = what is left.
3. Seeker chooses an integer order q per row that minimises the expected cost of week k+2:
   0.2 x leftover + 1 x lost sales, averaged over the scenarios.

The per-row problem is small and separable, so an exact answer by enumeration exists:
it is our oracle (H7). Seeker earns its place where enumeration does not scale:
the multi-week variant (order now plus a planned next order), joint constraints if we add
any, and the parameter tuning of phase 5.

### Phase 5: Policy tuning by historical simulation
At most a handful of global parameters, for example: a multiplier on the holding cost
(leftover is not wasted, it serves later weeks), the week-to-week correlation of the
scenarios, the number of weeks in the objective. Tuned by Seeker (or a small grid) on the
backtest games only (H4). Report mean and spread across games.

### Phase 6: Final exam (once)
Freeze the code, run `scripts/final_score.py` (official `vn2_play.py` on rounds 1-6), log
the result (H4), report it with the benchmark and the winner (H10). If the final score is far
better than the backtest gains, treat it as a warning sign, not a success (see the risk below).

### Phase 7: Write-up
FVA table (benchmark -> cleaning -> t0 -> policy), backtest vs final, what did and did not add value.

## 5. Risks and open questions

- **Possible contamination of t0-gamma.** The VN2 data was published on 29 September 2025;
  t0-gamma came out in 2026 and may have seen these sales, weeks 1-8 included, during
  pre-training. We cannot rule it out from the public docs. Mitigation: decide everything on
  backtests before 2024-04-08 and compare the final gain with the backtest gain.
- **Scored demand is censored too.** The competition scores weeks 1-8 with recorded sales, which
  are themselves capped by stock-outs. Forecasting unconstrained demand is right in principle;
  the backtest decides whether it pays here.
- **Sparse, intermittent rows.** Median demand is under one unit a week and 36 % of weeks have
  zero sales; quantile forecasts of small integers need care when turned into scenarios.
- **Running the tools.** Seeker needs your licence; t0-gamma needs a model download from
  Hugging Face, which this cloud session cannot reach. Both run on your machine; Claude writes the
  scripts and reads the outputs you send back.
